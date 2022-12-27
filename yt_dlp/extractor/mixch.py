from .common import InfoExtractor
from ..utils import UserNotLive, traverse_obj


class MixchIE(InfoExtractor):
    IE_NAME = 'mixch'
    _VALID_URL = r'https?://(?:www\.)?mixch\.tv/u/(?P<id>\d+)'

    _TESTS = [{
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
    }, {
        'url': 'https://mixch.tv/u/16137876/live',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://mixch.tv/u/{video_id}/live', video_id)

        initial_js_state = self._parse_json(self._search_regex(
            r'(?m)^\s*window\.__INITIAL_JS_STATE__\s*=\s*(\{.+?\});\s*$', webpage, 'initial JS state'), video_id)
        if not initial_js_state.get('liveInfo'):
            raise UserNotLive(video_id=video_id)

        return {
            'id': video_id,
            'title': traverse_obj(initial_js_state, ('liveInfo', 'title')),
            'comment_count': traverse_obj(initial_js_state, ('liveInfo', 'comments')),
            'view_count': traverse_obj(initial_js_state, ('liveInfo', 'visitor')),
            'timestamp': traverse_obj(initial_js_state, ('liveInfo', 'created')),
            'uploader': traverse_obj(initial_js_state, ('broadcasterInfo', 'name')),
            'uploader_id': video_id,
            'formats': [{
                'format_id': 'hls',
                'url': (traverse_obj(initial_js_state, ('liveInfo', 'hls'))
                        or f'https://d1hd0ww6piyb43.cloudfront.net/hls/torte_{video_id}.m3u8'),
                'ext': 'mp4',
                'protocol': 'm3u8',
            }],
            'is_live': True,
        }


class MixchArchiveIE(InfoExtractor):
    IE_NAME = 'mixch:archive'
    _VALID_URL = r'https?://(?:www\.)?mixch\.tv/archive/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://mixch.tv/archive/421',
        'skip': 'paid video, no DRM. expires at Jan 23',
        'info_dict': {
            'id': '421',
            'title': '96NEKO SHOW TIME',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        html5_videos = self._parse_html5_media_entries(
            url, webpage.replace('video-js', 'video'), video_id, 'hls')
        if not html5_videos:
            self.raise_login_required(method='cookies')
        infodict = html5_videos[0]
        infodict.update({
            'id': video_id,
            'title': self._html_search_regex(r'class="archive-title">(.+?)</', webpage, 'title')
        })

        return infodict
