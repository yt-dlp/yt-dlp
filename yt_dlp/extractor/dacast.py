import functools
import hashlib
import re
import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    classproperty,
    float_or_none,
    traverse_obj,
    url_or_none,
)


class DacastBaseIE(InfoExtractor):
    _URL_TYPE = None

    @classproperty
    def _VALID_URL(cls):
        return fr'https?://iframe\.dacast\.com/{cls._URL_TYPE}/(?P<user_id>[\w-]+)/(?P<id>[\w-]+)'

    @classproperty
    def _EMBED_REGEX(cls):
        return [rf'<iframe[^>]+\bsrc=["\'](?P<url>{cls._VALID_URL})']

    _API_INFO_URL = 'https://playback.dacast.com/content/info'

    @classmethod
    def _get_url_from_id(cls, content_id):
        user_id, media_id = content_id.split(f'-{cls._URL_TYPE}-')
        return f'https://iframe.dacast.com/{cls._URL_TYPE}/{user_id}/{media_id}'

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from super()._extract_embed_urls(url, webpage)
        for content_id in re.findall(
                rf'<script[^>]+\bsrc=["\']https://player\.dacast\.com/js/player\.js\?contentId=([\w-]+-{cls._URL_TYPE}-[\w-]+)["\']', webpage):
            yield cls._get_url_from_id(content_id)


class DacastVODIE(DacastBaseIE):
    _URL_TYPE = 'vod'
    _TESTS = [{
        'url': 'https://iframe.dacast.com/vod/acae82153ef4d7a7344ae4eaa86af534/1c6143e3-5a06-371d-8695-19b96ea49090',
        'info_dict': {
            'id': '1c6143e3-5a06-371d-8695-19b96ea49090',
            'ext': 'mp4',
            'uploader_id': 'acae82153ef4d7a7344ae4eaa86af534',
            'title': '2_4||Adnexal mass characterisation: O-RADS US and MRI||N. Bharwani, London/UK',
            'thumbnail': 'https://universe-files.dacast.com/26137208-5858-65c1-5e9a-9d6b6bd2b6c2',
        },
        'params': {'skip_download': 'm3u8'},
    }, {  # /uspaes/ in hls_url
        'url': 'https://iframe.dacast.com/vod/f9823fc6-faba-b98f-0d00-4a7b50a58c5b/348c5c84-b6af-4859-bb9d-1d01009c795b',
        'info_dict': {
            'id': '348c5c84-b6af-4859-bb9d-1d01009c795b',
            'ext': 'mp4',
            'title': 'pl1-edyta-rubas-211124.mp4',
            'uploader_id': 'f9823fc6-faba-b98f-0d00-4a7b50a58c5b',
            'thumbnail': 'https://universe-files.dacast.com/4d0bd042-a536-752d-fc34-ad2fa44bbcbb.png',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.dacast.com/support/knowledgebase/how-can-i-embed-a-video-on-my-website/',
        'info_dict': {
            'id': 'b6674869-f08a-23c5-1d7b-81f5309e1a90',
            'ext': 'mp4',
            'title': '4-HowToEmbedVideo.mp4',
            'uploader_id': '3b67c4a9-3886-4eb1-d0eb-39b23b14bef3',
            'thumbnail': 'https://universe-files.dacast.com/d26ab48f-a52a-8783-c42e-a90290ba06b6.png',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://gist.githubusercontent.com/bashonly/4ad249ef2910346fbdf3809b220f11ee/raw/87349778d4af1a80b1fcc3beb9c88108de5858f5/dacast_embeds.html',
        'info_dict': {
            'id': 'e7df418e-a83b-7a7f-7b5e-1a667981e8fa',
            'ext': 'mp4',
            'title': 'Evening Service 2-5-23',
            'uploader_id': '943bb1ab3c03695ba85330d92d6d226e',
            'thumbnail': 'https://universe-files.dacast.com/337472b3-e92c-2ea4-7eb7-5700da477f67',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    @functools.cached_property
    def _usp_signing_secret(self):
        player_js = self._download_webpage(
            'https://player.dacast.com/js/player.js', None, 'Downloading player JS')
        # Rotates every so often, but hardcode a fallback in case of JS change/breakage before rotation
        return self._search_regex(
            r'\bUSP_SIGNING_SECRET\s*=\s*(["\'])(?P<secret>(?:(?!\1).)+)', player_js,
            'usp signing secret', group='secret', fatal=False) or 'odnInCGqhvtyRTtIiddxtuRtawYYICZP'

    def _real_extract(self, url):
        user_id, video_id = self._match_valid_url(url).group('user_id', 'id')
        query = {'contentId': f'{user_id}-vod-{video_id}', 'provider': 'universe'}
        info = self._download_json(self._API_INFO_URL, video_id, query=query, fatal=False)
        access = self._download_json(
            'https://playback.dacast.com/content/access', video_id,
            note='Downloading access JSON', query=query, expected_status=403)

        error = access.get('error')
        if error in ('Broadcaster has been blocked', 'Content is offline'):
            raise ExtractorError(error, expected=True)
        elif error:
            raise ExtractorError(f'Dacast API says "{error}"')

        hls_url = access['hls']
        hls_aes = {}

        if 'DRM_EXT' in hls_url:
            self.report_drm(video_id)
        elif '/uspaes/' in hls_url:
            # Ref: https://player.dacast.com/js/player.js
            ts = int(time.time())
            signature = hashlib.sha1(
                f'{10413792000 - ts}{ts}{self._usp_signing_secret}'.encode()).digest().hex()
            hls_aes['uri'] = f'https://keys.dacast.com/uspaes/{video_id}.key?s={signature}&ts={ts}'

        for retry in self.RetryManager():
            try:
                formats = self._extract_m3u8_formats(hls_url, video_id, 'mp4', m3u8_id='hls')
            except ExtractorError as e:
                # CDN will randomly respond with 403
                if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                    retry.error = e
                    continue
                raise

        return {
            'id': video_id,
            'uploader_id': user_id,
            'formats': formats,
            'hls_aes': hls_aes or None,
            **traverse_obj(info, ('contentInfo', {
                'title': 'title',
                'duration': ('duration', {float_or_none}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
            })),
        }


class DacastPlaylistIE(DacastBaseIE):
    _URL_TYPE = 'playlist'
    _TESTS = [{
        'url': 'https://iframe.dacast.com/playlist/943bb1ab3c03695ba85330d92d6d226e/b632eb053cac17a9c9a02bcfc827f2d8',
        'playlist_mincount': 28,
        'info_dict': {
            'id': 'b632eb053cac17a9c9a02bcfc827f2d8',
            'title': 'Archive Sermons',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://gist.githubusercontent.com/bashonly/7efb606f49f3c6e07ea0327de5a661d1/raw/05a16eac830245ea301fb0a585023bec71e6093c/dacast_playlist_embed.html',
        'playlist_mincount': 28,
        'info_dict': {
            'id': 'b632eb053cac17a9c9a02bcfc827f2d8',
            'title': 'Archive Sermons',
        },
    }]

    def _real_extract(self, url):
        user_id, playlist_id = self._match_valid_url(url).group('user_id', 'id')
        info = self._download_json(
            self._API_INFO_URL, playlist_id, note='Downloading playlist JSON', query={
                'contentId': f'{user_id}-playlist-{playlist_id}',
                'provider': 'universe',
            })['contentInfo']

        def entries(info):
            for video in traverse_obj(info, ('features', 'playlist', 'contents', lambda _, v: v['id'])):
                yield self.url_result(
                    DacastVODIE._get_url_from_id(video['id']), DacastVODIE, video['id'], video.get('title'))

        return self.playlist_result(entries(info), playlist_id, info.get('title'))
