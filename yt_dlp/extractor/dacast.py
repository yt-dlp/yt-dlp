import hashlib
import re
import time
import urllib.error

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    traverse_obj,
    url_or_none,
)


class DacastIE(InfoExtractor):
    _VALID_URL = r'https?://iframe\.dacast\.com/vod/(?P<user_id>[\w-]+)/(?P<id>[\w-]+)'
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
    }]

    @staticmethod
    def _get_url_from_id(content_id):
        url_type = 'playlist' if '-playlist-' in content_id else 'vod'
        user_id, media_id = content_id.split(f'-{url_type}-')
        return f'https://iframe.dacast.com/{url_type}/{user_id}/{media_id}'

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for content_id in re.findall(
                r'<script[^>]+\bsrc=["\']https://player\.dacast\.com/js/player\.js\?contentId=([\w-]+-vod-[\w-]+)["\']', webpage):
            yield DacastIE._get_url_from_id(content_id)

    def _real_extract(self, url):
        user_id, video_id = self._match_valid_url(url).group('user_id', 'id')
        query = {'contentId': f'{user_id}-vod-{video_id}', 'provider': 'universe'}
        info = self._download_json(
            'https://playback.dacast.com/content/info', video_id, query=query, fatal=False)
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
            # From https://player.dacast.com/js/player.js
            ts = int(time.time())
            signature = hashlib.sha1(
                f'{10413792000 - ts}{ts}YfaKtquEEpDeusCKbvYszIEZnWmBcSvw').digest().hex()
            hls_aes['uri'] = f'https://keys.dacast.com/uspaes/{video_id}.key?s={signature}&ts={ts}'

        for retry in self.RetryManager():
            try:
                formats = self._extract_m3u8_formats(hls_url, video_id, 'mp4', m3u8_id='hls')
            except ExtractorError as e:
                # CDN will randomly respond with 403
                if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 403:
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


class DacastPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://iframe\.dacast\.com/playlist/(?P<user_id>[\w-]+)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://iframe.dacast.com/playlist/943bb1ab3c03695ba85330d92d6d226e/b632eb053cac17a9c9a02bcfc827f2d8',
        'playlist_mincount': 28,
        'info_dict': {
            'id': 'b632eb053cac17a9c9a02bcfc827f2d8',
            'title': 'Archive Sermons',
        },
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for content_id in re.findall(
                r'<script[^>]+\bsrc=["\']https://player\.dacast\.com/js/player\.js\?contentId=([\w-]+-playlist-[\w-]+)["\']', webpage):
            yield DacastIE._get_url_from_id(content_id)

    def _real_extract(self, url):
        user_id, playlist_id = self._match_valid_url(url).group('user_id', 'id')
        info = self._download_json(
            'https://playback.dacast.com/content/info', playlist_id, query={
                'contentId': f'{user_id}-playlist-{playlist_id}',
                'provider': 'universe',
            })['contentInfo']

        def entries(info):
            for video in traverse_obj(info, ('features', 'playlist', 'contents', lambda _, v: v['id'])):
                yield self.url_result(
                    DacastIE._get_url_from_id(video['id']), DacastIE, video['id'], video.get('title'))

        return self.playlist_result(entries(info), playlist_id, info.get('title'))
