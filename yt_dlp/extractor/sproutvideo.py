import base64
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    remove_start,
    smuggle_url,
    unsmuggle_url,
    update_url_query,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class SproutVideoIE(InfoExtractor):
    _NO_SCHEME_RE = r'//videos\.sproutvideo\.com/embed/(?P<id>[\da-f]+)/[\da-f]+'
    _VALID_URL = rf'https?:{_NO_SCHEME_RE}'
    _EMBED_REGEX = [rf'<iframe [^>]*\bsrc=["\'](?P<url>(?:https?:)?{_NO_SCHEME_RE}[^"\']*)["\']']
    _TESTS = [{
        'url': 'https://videos.sproutvideo.com/embed/4c9dddb01910e3c9c4/0fc24387c4f24ee3',
        'md5': '1343ce1a6cb39d67889bfa07c7b02b0e',
        'info_dict': {
            'id': '4c9dddb01910e3c9c4',
            'ext': 'mp4',
            'title': 'Adrien Labaeye : Berlin, des communautés aux communs',
            'duration': 576,
            'thumbnail': r're:https?://images\.sproutvideo\.com/.+\.jpg',
        },
    }, {
        'url': 'https://videos.sproutvideo.com/embed/a79fdcb21f1be2c62e/93bf31e41e39ca27',
        'md5': 'cebae5cf558cca83271917cf4ec03f26',
        'info_dict': {
            'id': 'a79fdcb21f1be2c62e',
            'ext': 'mp4',
            'title': 'HS_01_Live Stream 2023-01-14 10:00',
            'duration': 703,
            'thumbnail': r're:https?://images\.sproutvideo\.com/.+\.jpg',
        },
        'skip': 'Account Disabled',
    }, {
        # http formats 'sd' and 'hd' are available
        'url': 'https://videos.sproutvideo.com/embed/119cd6bc1a18e6cd98/30751a1761ae5b90',
        'md5': 'f368c78df07e78a749508b221528672c',
        'info_dict': {
            'id': '119cd6bc1a18e6cd98',
            'ext': 'mp4',
            'title': '3. Updating your Partner details',
            'thumbnail': r're:https?://images\.sproutvideo\.com/.+\.jpg',
            'duration': 60,
        },
        'params': {'format': 'hd'},
    }, {
        # subtitles
        'url': 'https://videos.sproutvideo.com/embed/119dd8ba121ee0cc98/4ee50c88a343215d?type=hd',
        'md5': '7f6798f037d7a3e3e07e67959de68fc6',
        'info_dict': {
            'id': '119dd8ba121ee0cc98',
            'ext': 'mp4',
            'title': 'Recipients Setup - Domestic Wire Only',
            'thumbnail': r're:https?://images\.sproutvideo\.com/.+\.jpg',
            'duration': 77,
            'subtitles': {'en': 'count:1'},
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.solidarum.org/vivre-ensemble/adrien-labaeye-berlin-des-communautes-aux-communs',
        'info_dict': {
            'id': '4c9dddb01910e3c9c4',
            'ext': 'mp4',
            'title': 'Adrien Labaeye : Berlin, des communautés aux communs',
            'duration': 576,
            'thumbnail': r're:https?://images\.sproutvideo\.com/.+\.jpg',
        },
    }]
    _M3U8_URL_TMPL = 'https://{base}.videos.sproutvideo.com/{s3_user_hash}/{s3_video_hash}/video/index.m3u8'
    _QUALITIES = ('hd', 'uhd', 'source')  # Exclude 'sd' to prioritize hls formats above it

    @staticmethod
    def _policy_to_qs(policy, signature_key, as_string=False):
        query = {}
        for key, value in policy['signatures'][signature_key].items():
            query[remove_start(key, 'CloudFront-')] = value
        query['sessionID'] = policy['sessionID']
        return urllib.parse.urlencode(query, doseq=True) if as_string else query

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for embed_url in super()._extract_embed_urls(url, webpage):
            if embed_url.startswith('//'):
                embed_url = f'https:{embed_url}'
            yield smuggle_url(embed_url, {'referer': url})

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, headers={
            **traverse_obj(smuggled_data, {'Referer': 'referer'}),
            # yt-dlp's default Chrome user-agents are too old
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:140.0) Gecko/20100101 Firefox/140.0',
        })
        data = self._search_json(
            r'var\s+(?:dat|playerInfo)\s*=\s*["\']', webpage, 'player info', video_id,
            contains_pattern=r'[A-Za-z0-9+/=]+', end_pattern=r'["\'];',
            transform_source=lambda x: base64.b64decode(x).decode())

        # SproutVideo may send player info for 'SMPTE Color Monitor Test' [a791d7b71b12ecc52e]
        # e.g. if the user-agent we used with the webpage request is too old
        video_uid = data['videoUid']
        if video_id != video_uid:
            raise ExtractorError(f'{self.IE_NAME} sent the wrong video data ({video_uid})')

        formats, subtitles = [], {}
        headers = {
            'Accept': '*/*',
            'Origin': 'https://videos.sproutvideo.com',
            'Referer': url,
        }

        # HLS extraction is fatal; only attempt it if the JSON data says it's available
        if traverse_obj(data, 'hls'):
            manifest_query = self._policy_to_qs(data, 'm')
            fragment_query = self._policy_to_qs(data, 't', as_string=True)
            key_query = self._policy_to_qs(data, 'k', as_string=True)

            formats.extend(self._extract_m3u8_formats(
                self._M3U8_URL_TMPL.format(**data), video_id, 'mp4',
                m3u8_id='hls', headers=headers, query=manifest_query))
            for fmt in formats:
                fmt.update({
                    'url': update_url_query(fmt['url'], manifest_query),
                    'extra_param_to_segment_url': fragment_query,
                    'extra_param_to_key_url': key_query,
                })

        if downloads := traverse_obj(data, ('downloads', {dict.items}, lambda _, v: url_or_none(v[1]))):
            quality = qualities(self._QUALITIES)
            acodec = 'none' if data.get('has_audio') is False else None
            formats.extend([{
                'format_id': str(format_id),
                'url': format_url,
                'ext': 'mp4',
                'quality': quality(format_id),
                'acodec': acodec,
            } for format_id, format_url in downloads])

        for sub_data in traverse_obj(data, ('subtitleData', lambda _, v: url_or_none(v['src']))):
            subtitles.setdefault(sub_data.get('srclang', 'en'), []).append({
                'url': sub_data['src'],
            })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': headers,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'duration': ('duration', {int_or_none}),
                'thumbnail': ('posterframe_url', {url_or_none}),
            }),
        }


class VidsIoIE(InfoExtractor):
    IE_NAME = 'vids.io'
    _VALID_URL = r'https?://[\w-]+\.vids\.io/videos/(?P<id>[\da-f]+)/(?P<display_id>[\w-]+)'
    _TESTS = [{
        'url': 'https://how-to-video.vids.io/videos/799cd8b11c10efc1f0/how-to-video-live-streaming',
        'md5': '9bbbb2c0c0739eb163b80f87b8d77c9e',
        'info_dict': {
            'id': '799cd8b11c10efc1f0',
            'ext': 'mp4',
            'title': 'How to Video: Live Streaming',
            'duration': 2787,
            'thumbnail': r're:https?://images\.sproutvideo\.com/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage, urlh = self._download_webpage_handle(url, display_id, expected_status=403)

        if urlh.status == 403:
            password = self.get_param('videopassword')
            if not password:
                raise ExtractorError(
                    'This video is password-protected; use the --video-password option', expected=True)
            try:
                webpage = self._download_webpage(
                    url, display_id, 'Submitting video password',
                    data=urlencode_postdata({
                        'password': password,
                        **self._hidden_inputs(webpage),
                    }))
                # Requests with user's session cookie `_sproutvideo_session` are now authorized
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                    raise ExtractorError('Incorrect password', expected=True)
                raise

        if embed_url := next(SproutVideoIE._extract_embed_urls(url, webpage), None):
            return self.url_result(embed_url, SproutVideoIE, video_id)

        raise ExtractorError('Unable to extract any SproutVideo embed url')
