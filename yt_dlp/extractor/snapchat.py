from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class SnapchatBaseIE(InfoExtractor):
    def _parse_formats(self, video_id, data):
        video_data = {}
        formats = []
        if snap_list := data.get('snapList'):
            video_data = traverse_obj(snap_list, (lambda _, v: v.get('snapId', {}).get('value') == video_id, any))
        video_data = video_data if video_data else data
        formats.append({
            **traverse_obj(video_data, ('videoMetadata', {
                'url': ('contentUrl', {url_or_none}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
            }), ('snapUrls', {
                'url': ('mediaUrl', {url_or_none}),
            })),
            'ext': 'mp4',
        })
        # Only for snapchat discover.
        if m3u8_url := traverse_obj(data, ('videoTrackUrl', 'value')):
            formats, _ = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id)
            formats.extend(formats)
        return formats

    def _parse_metadata(self, data):
        return {
            **traverse_obj(data, ('videoMetadata', {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'timestamp': ('uploadDateMs', {float_or_none(scale=1000)}),
                'view_count': ('viewCount', {int_or_none}, {lambda x: None if x == -1 else x}),
                'repost_count': ('shareCount', {int_or_none}),
                'duration': ('durationMs', {float_or_none(scale=1000)}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
                'uploader': ('creator', 'personCreator', 'username', {str}),
                'uploader_url': ('creator', 'personCreator', 'url', {url_or_none}),
            })),
            **traverse_obj(data, ({
                'title': ('storyTitle', 'value', {str}),
            })),
        }


class SnapchatSpotlightIE(SnapchatBaseIE):
    _VALID_URL = r'https?://(?:www\.)?snapchat\.com/(?:@[^/]+/)?spotlight/(?P<id>[^/?#&]+)'
    IE_NAME = 'snapchat:spotlight'

    _TESTS = [{
        'url': 'https://www.snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYYWtidGhudGZpAX1TKn0JAX1TKnXJAAAAAA',
        'md5': '401e2841f6e055ced4fd7aafb041d86b',
        'info_dict': {
            'id': 'W7_EDlXWTBiXAEEniNoMPwAAYYWtidGhudGZpAX1TKn0JAX1TKnXJAAAAAA',
            'ext': 'mp4',
            'title': 'Views 💕',
            'description': '',
            'uploader': 'shreypatel57',
            'uploader_url': 'https://www.snapchat.com/add/shreypatel57',
            'repost_count': int,
            'duration': 4.665,
            'thumbnail': 'https://cf-st.sc-cdn.net/d/kKJHIR1QAznRKK9jgYYDq.256.IRZXSOY?mo=GjwaFRoAGgAiBgin0YOrBjIBBEgCUC5gAVoQRGZMYXJnZVRodW1ibmFpbKIBEAiAAiILEgAqB0lSWlhTT1k%3D&uc=46',
            'timestamp': 1637777831.369,
            'upload_date': '20211124',
        },
    }, {
        'url': 'https://www.snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYdWdvZ3NkeG15AZnzjnnVAZnzjnY2AAAAAQ',
        'md5': '411312c2a234bbc701605a5935808cf8',
        'info_dict': {
            'id': 'W7_EDlXWTBiXAEEniNoMPwAAYdWdvZ3NkeG15AZnzjnnVAZnzjnY2AAAAAQ',
            'ext': 'mp4',
            'title': 'Spotlight Snap',
            'description': '',
            'uploader': 'benreidsoccer',
            'uploader_url': 'https://www.snapchat.com/add/benreidsoccer',
            'view_count': int,
            'repost_count': int,
            'duration': 21.37,
            'thumbnail': 'https://cf-st.sc-cdn.net/d/xn7pQbeaVUe5p2LwELrbh.256.IRZXSOY?mo=GkYaCTIBBEgCUC5gAVCgAVoQRGZMYXJnZVRodW1ibmFpbKIBEAiAAiILEgAqB0lSWlhTT1miARAImgoiCxIAKgdJUlpYU09Z&uc=46',
            'timestamp': 1760727823.926,
            'upload_date': '20251017',
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
            'formats': self._parse_formats(video_id, video_data),
            **traverse_obj(video_data, ('videoMetadata', {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'timestamp': ('uploadDateMs', {float_or_none(scale=1000)}),
                'view_count': ('viewCount', {int_or_none}, {lambda x: None if x == -1 else x}),
                'repost_count': ('shareCount', {int_or_none}),
                'duration': ('durationMs', {float_or_none(scale=1000)}),
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


class SnapchatDiscoverIE(SnapchatBaseIE):
    _VALID_URL = r'https?://(?:www\.)?snapchat\.com/p/[^/]+/(?P<id>[^/?#&]+)'
    IE_NAME = 'snapchat:discover'

    _TESTS = [{
        'url': 'https://www.snapchat.com/p/2508f100-9394-49ea-8aa8-71d97fc82fd8/1536428196673536',
        'info_dict': {
            'id': '1536428196673536',
            'ext': 'mp4',
            'title': 'Best Cleaning of Sneakers 🤯',
            'thumbnail': r're:https://[^.]+.appspot\.com/.+',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.snapchat.com/p/f3d6a5f8-540e-4f6f-864d-bfbbab247b68/1536439338983424',
        'info_dict': {
            'id': '1536439338983424',
            'ext': 'mp4',
            'title': 'When Your Hair Take Over The Room💯😍',
            'thumbnail': r're:https://[^.]+.appspot\.com/.+',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        page_props = self._search_nextjs_data(webpage, video_id)['props']['pageProps']
        video_data = traverse_obj(page_props, (
            'preselectedStory', 'premiumStory', 'playerStory'))
        return {
            'id': video_id,
            'formats': self._parse_formats(video_id, video_data),
            **self._parse_metadata(video_data),
        }


class SnapchatProfileIE(SnapchatBaseIE):
    _VALID_URL = r'https?://(?:www\.)?snapchat\.com/@(?P<username>[\w.]+)'
    _TESTS = [{
        'url': 'https://www.snapchat.com/@ahmedhossam_1',
        'info_dict': {
            'id': 'ahmedhossam_1',
            'title': 'ahmedhossam_1',
        },
        'playlist_count': 16,
    }, {
        'url': 'https://www.snapchat.com/@zoerhodee',
        'only_matching': True,
    }]

    def _entries(self, data):
        for post in data:
            video_id = self._search_regex(
                r'spotlight/(\w+)', traverse_obj(post, ('oneLinkParams', 'deepLinkUrl')),
                'video_id')
            yield {
                'id': video_id,
                'formats': self._parse_formats(video_id, post),
                **self._parse_metadata(post),
            }

    def _real_extract(self, url):
        username = self._match_valid_url(url).group('username')
        webpage = self._download_webpage(url, username)
        data = self._search_nextjs_data(webpage, username)
        all_videos = traverse_obj(data, ('props', 'pageProps', 'spotlightStoryMetadata'))
        return self.playlist_result(
            self._entries(all_videos), username, username)
