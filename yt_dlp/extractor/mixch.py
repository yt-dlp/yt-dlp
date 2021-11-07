from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
)


class MixchIE(InfoExtractor):
    IE_NAME = 'mixch'
    # allow omitting last /live in the URL, though it's likely uncommon
    _VALID_URL = r'https?://(?:www\.)?mixch\.tv/u/(?P<id>\d+)'

    TESTS = [{
        'url': 'https://mixch.tv/u/16137876/live',
        'skip': 'live has ended',
    }, {
        'url': 'https://mixch.tv/u/16236849/live',
        'skip': 'don\'t know if this live persists',
        'info_dict': {
            'id': '16236849',
            'title': '24配信シェア⭕️投票🙏💦',
            'comment_count': 13145,
            'view_count': 28348,
            'timestamp': 1636189377,
            'uploader': '🦥伊咲👶🏻#フレアワ',
            'uploader_id': '16236849',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://mixch.tv/u/%s/live' % video_id
        webpage = self._download_webpage(url, video_id)

        initial_js_state = self._parse_json(self._search_regex(
            r'(?m)^\s*window\.__INITIAL_JS_STATE__\s*=\s*(\{.+?\});\s*$', webpage, 'initial JS state'), video_id)
        if not initial_js_state.get('liveInfo'):
            raise ExtractorError('Live has ended.', expected=True)

        # the service does not provide alternative resolutions
        hls_url = traverse_obj(initial_js_state, ('liveInfo', 'hls')) or 'https://d1hd0ww6piyb43.cloudfront.net/hls/torte_%s.m3u8' % video_id
        formats = self._extract_m3u8_formats(
            hls_url, video_id, ext='mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'title': traverse_obj(initial_js_state, ('liveInfo', 'title')),
            'comment_count': traverse_obj(initial_js_state, ('liveInfo', 'comments')),
            'view_count': traverse_obj(initial_js_state, ('liveInfo', 'visitor')),
            'timestamp': traverse_obj(initial_js_state, ('liveInfo', 'created')),
            'uploader': traverse_obj(initial_js_state, ('broadcasterInfo', 'name')),
            'uploader_id': video_id,
            'formats': formats,
            'is_live': True,
            'webpage_url': url,
        }
