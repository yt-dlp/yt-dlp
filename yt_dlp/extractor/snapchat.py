from .common import InfoExtractor
from ..utils import float_or_none, int_or_none, url_or_none
from ..utils.traversal import traverse_obj


class SnapchatSpotlightIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?snapchat\.com/spotlight/(?P<id>\w+)'

    _TESTS = [{
        'url': 'https://www.snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYYWtidGhudGZpAX1TKn0JAX1TKnXJAAAAAA',
        'md5': '46c580f63592d0cbb76e974d2f9f0fcc',
        'info_dict': {
            'id': 'W7_EDlXWTBiXAEEniNoMPwAAYYWtidGhudGZpAX1TKn0JAX1TKnXJAAAAAA',
            'ext': 'mp4',
            'title': 'Views 💕',
            'description': '',
            'thumbnail': r're:https://cf-st\.sc-cdn\.net/d/kKJHIR1QAznRKK9jgYYDq\.256\.IRZXSOY',
            'duration': 4.665,
            'timestamp': 1637777831.369,
            'upload_date': '20211124',
            'repost_count': int,
            'uploader': 'shreypatel57',
            'uploader_url': 'https://www.snapchat.com/add/shreypatel57',
        },
    }, {
        'url': 'https://www.snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYcnVjYWdwcGV1AZEaIYn5AZEaIYnrAAAAAQ',
        'md5': '4cd9626458c1a0e3e6dbe72c544a9ec2',
        'info_dict': {
            'id': 'W7_EDlXWTBiXAEEniNoMPwAAYcnVjYWdwcGV1AZEaIYn5AZEaIYnrAAAAAQ',
            'ext': 'mp4',
            'title': 'Spotlight Snap',
            'description': 'How he flirt her teacher🤭🤭🤩😍 #kdrama#cdrama #dramaclips #dramaspotlight',
            'thumbnail': r're:https://cf-st\.sc-cdn\.net/i/ztfr6xFs0FOcFhwVczWfj\.256\.IRZXSOY',
            'duration': 10.91,
            'timestamp': 1722720291.307,
            'upload_date': '20240803',
            'view_count': int,
            'repost_count': int,
            'uploader': 'ganda0535',
            'uploader_url': 'https://www.snapchat.com/add/ganda0535',
            'tags': ['#dramaspotlight', '#dramaclips', '#cdrama', '#kdrama'],
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        page_props = self._search_nextjs_data(webpage, video_id)['props']['pageProps']
        video_data = traverse_obj(page_props, (
            'spotlightFeed', 'spotlightStories',
            lambda _, v: v['story']['storyId']['value'] == video_id, 'metadata', any), None)

        return {
            'id': video_id,
            'ext': 'mp4',
            **traverse_obj(video_data, ('videoMetadata', {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'timestamp': ('uploadDateMs', {lambda x: float_or_none(x, 1000)}),
                'view_count': ('viewCount', {int_or_none}, {lambda x: None if x == -1 else x}),
                'repost_count': ('shareCount', {int_or_none}),
                'url': ('contentUrl', {url_or_none}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
                'duration': ('durationMs', {lambda x: float_or_none(x, 1000)}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
                'uploader': ('creator', 'personCreator', 'username', {str}),
                'uploader_url': ('creator', 'personCreator', 'url', {url_or_none}),
            })),
            **traverse_obj(video_data, {
                'description': ('description', {str}),
                'tags': ('hashtags', ..., {str}),
                'view_count': ('engagementStats', 'viewCount', {int_or_none}, {lambda x: None if x == -1 else x}),
                'repost_count': ('engagementStats', 'shareCount', {int_or_none}),
            }),
        }
