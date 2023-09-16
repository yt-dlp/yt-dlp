import base64

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    traverse_obj,
)


class ChilloutzoneIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?chilloutzone\.net/video/(?P<id>[\w-]+)\.html'
    _TESTS = [{
        'url': 'https://www.chilloutzone.net/video/enemene-meck-alle-katzen-weg.html',
        'md5': 'a76f3457e813ea0037e5244f509e66d1',
        'info_dict': {
            'id': 'enemene-meck-alle-katzen-weg',
            'ext': 'mp4',
            'title': 'Enemene Meck - Alle Katzen weg',
            'description': 'Ist das der Umkehrschluss des Niesenden Panda-Babys?',
            'duration': 24,
        },
    }, {
        'note': 'Video hosted at YouTube',
        'url': 'https://www.chilloutzone.net/video/eine-sekunde-bevor.html',
        'info_dict': {
            'id': '1YVQaAgHyRU',
            'ext': 'mp4',
            'title': '16 Photos Taken 1 Second Before Disaster',
            'description': 'md5:58a8fcf6a459fe0a08f54140f0ad1814',
            'uploader': 'BuzzFeedVideo',
            'uploader_id': '@BuzzFeedVideo',
            'upload_date': '20131105',
            'availability': 'public',
            'thumbnail': 'https://i.ytimg.com/vi/1YVQaAgHyRU/maxresdefault.jpg',
            'tags': 'count:41',
            'like_count': int,
            'playable_in_embed': True,
            'channel_url': 'https://www.youtube.com/channel/UCpko_-a4wgz2u_DgDgd9fqA',
            'chapters': 'count:6',
            'live_status': 'not_live',
            'view_count': int,
            'categories': ['Entertainment'],
            'age_limit': 0,
            'channel_id': 'UCpko_-a4wgz2u_DgDgd9fqA',
            'duration': 100,
            'uploader_url': 'http://www.youtube.com/@BuzzFeedVideo',
            'channel_follower_count': int,
            'channel': 'BuzzFeedVideo',
        },
    }, {
        'url': 'https://www.chilloutzone.net/video/icon-blending.html',
        'md5': '2f9d6850ec567b24f0f4fa143b9aa2f9',
        'info_dict': {
            'id': 'LLNkHpSjBfc',
            'ext': 'mp4',
            'title': 'The Sunday Times   Making of Icons',
            'description': 'md5:b9259fcf63a1669e42001e5db677f02a',
            'uploader': 'MadFoxUA',
            'uploader_id': '@MadFoxUA',
            'upload_date': '20140204',
            'channel_id': 'UCSZa9Y6-Vl7c11kWMcbAfCw',
            'channel_url': 'https://www.youtube.com/channel/UCSZa9Y6-Vl7c11kWMcbAfCw',
            'comment_count': int,
            'uploader_url': 'http://www.youtube.com/@MadFoxUA',
            'duration': 66,
            'live_status': 'not_live',
            'channel_follower_count': int,
            'playable_in_embed': True,
            'view_count': int,
            'like_count': int,
            'thumbnail': 'https://i.ytimg.com/vi/LLNkHpSjBfc/maxresdefault.jpg',
            'categories': ['Comedy'],
            'availability': 'public',
            'tags': [],
            'channel': 'MadFoxUA',
            'age_limit': 0,
        },
    }, {
        'url': 'https://www.chilloutzone.net/video/ordentlich-abgeschuettelt.html',
        'info_dict': {
            'id': 'ordentlich-abgeschuettelt',
            'ext': 'mp4',
            'title': 'Ordentlich abgeschüttelt',
            'description': 'md5:d41541966b75d3d1e8ea77a94ea0d329',
            'duration': 18,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        b64_data = self._html_search_regex(
            r'var cozVidData\s*=\s*"([^"]+)"', webpage, 'video data')
        info = self._parse_json(base64.b64decode(b64_data).decode(), video_id)

        video_url = info.get('mediaUrl')
        native_platform = info.get('nativePlatform')

        if native_platform and info.get('sourcePriority') == 'native':
            native_video_id = info['nativeVideoId']
            if native_platform == 'youtube':
                return self.url_result(native_video_id, 'Youtube')
            elif native_platform == 'vimeo':
                return self.url_result(f'https://vimeo.com/{native_video_id}', 'Vimeo')

        elif not video_url:
            # Possibly a standard youtube embed?
            # TODO: Investigate if site still does this (there are no tests for it)
            return self.url_result(url, 'Generic')

        return {
            'id': video_id,
            'url': video_url,
            'ext': 'mp4',
            **traverse_obj(info, {
                'title': 'title',
                'description': ('description', {clean_html}),
                'duration': ('videoLength', {int_or_none}),
                'width': ('videoWidth', {int_or_none}),
                'height': ('videoHeight', {int_or_none}),
            }),
        }
