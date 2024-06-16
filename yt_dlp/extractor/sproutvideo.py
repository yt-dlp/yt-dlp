import base64
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
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
        webpage = self._download_webpage(
            url, video_id, headers=traverse_obj(smuggled_data, {'Referer': 'referer'}))
        data = self._search_json(
            r'var\s+dat\s*=\s*["\']', webpage, 'data', video_id, contains_pattern=r'[A-Za-z0-9+/=]+',
            end_pattern=r'["\'];', transform_source=lambda x: base64.b64decode(x).decode())

        query = self._policy_to_qs(data, 'm')
        headers = {
            'Accept': '*/*',
            'Origin': 'https://videos.sproutvideo.com',
            'Referer': url,
        }

        formats = self._extract_m3u8_formats(
            self._M3U8_URL_TMPL.format(**data), video_id, 'mp4',
            m3u8_id='hls', headers=headers, query=query)
        for fmt in formats:
            fmt['url'] = update_url_query(fmt['url'], query)

        return {
            'id': video_id,
            'formats': formats,
            'extra_param_to_segment_url': self._policy_to_qs(data, 't', as_string=True),
            'extra_param_to_key_url': self._policy_to_qs(data, 'k', as_string=True),
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
