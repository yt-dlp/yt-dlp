from .common import InfoExtractor
from .rumble import RumbleEmbedIE
from .youtube import YoutubeIE
from ..utils import ExtractorError, clean_html, get_element_by_class, strip_or_none


class Funker530IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?funker530\.com/video/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://funker530.com/video/azov-patrol-caught-in-open-under-automatic-grenade-launcher-fire/',
        'md5': '085f50fea27523a388bbc22e123e09c8',
        'info_dict': {
            'id': 'v2qbmu4',
            'ext': 'mp4',
            'title': 'Azov Patrol Caught In Open Under Automatic Grenade Launcher Fire',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Funker530',
            'channel': 'Funker530',
            'channel_url': 'https://rumble.com/c/c-1199543',
            'width': 1280,
            'height': 720,
            'fps': 25,
            'duration': 27,
            'upload_date': '20230608',
            'timestamp': 1686241321,
            'live_status': 'not_live',
            'description': 'md5:bea2e1f458095414e04b5ac189c2f980',
        }
    }, {
        'url': 'https://funker530.com/video/my-friends-joined-the-russians-civdiv/',
        'md5': 'a42c2933391210662e93e867d7124b70',
        'info_dict': {
            'id': 'k-pk4bOvoac',
            'ext': 'mp4',
            'view_count': int,
            'channel': 'Civ Div',
            'comment_count': int,
            'channel_follower_count': int,
            'thumbnail': 'https://i.ytimg.com/vi/k-pk4bOvoac/maxresdefault.jpg',
            'uploader_id': '@CivDiv',
            'duration': 357,
            'channel_url': 'https://www.youtube.com/channel/UCgsCiwJ88up-YyMHo7hL5-A',
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@CivDiv',
            'channel_id': 'UCgsCiwJ88up-YyMHo7hL5-A',
            'like_count': int,
            'description': 'md5:aef75ec3f59c07a0e39400f609b24429',
            'live_status': 'not_live',
            'age_limit': 0,
            'uploader': 'Civ Div',
            'categories': ['People & Blogs'],
            'title': 'My “Friends” joined the Russians.',
            'availability': 'public',
            'upload_date': '20230608',
            'playable_in_embed': True,
            'heatmap': 'count:100',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        info = {}
        rumble_url = list(RumbleEmbedIE._extract_embed_urls(url, webpage))
        if rumble_url:
            info = {'url': rumble_url[0], 'ie_key': RumbleEmbedIE.ie_key()}
        else:
            youtube_url = list(YoutubeIE._extract_embed_urls(url, webpage))
            if youtube_url:
                info = {'url': youtube_url[0], 'ie_key': YoutubeIE.ie_key()}
        if not info:
            raise ExtractorError('No videos found on webpage', expected=True)

        return {
            **info,
            '_type': 'url_transparent',
            'description': strip_or_none(self._search_regex(
                r'(?s)(.+)About the Author', clean_html(get_element_by_class('video-desc-paragraph', webpage)),
                'description', default=None))
        }
