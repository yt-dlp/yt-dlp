import urllib.parse

from ._tab import YoutubeTabBaseInfoExtractor
from ..common import SearchInfoExtractor
from ...utils import join_nonempty, parse_qs


class YoutubeSearchIE(YoutubeTabBaseInfoExtractor, SearchInfoExtractor):
    IE_DESC = 'YouTube search'
    IE_NAME = 'youtube:search'
    _SEARCH_KEY = 'ytsearch'
    _SEARCH_PARAMS = 'EgIQAfABAQ=='  # Videos only
    _TESTS = [{
        'url': 'ytsearch5:youtube-dl test video',
        'playlist_count': 5,
        'info_dict': {
            'id': 'youtube-dl test video',
            'title': 'youtube-dl test video',
        },
    }, {
        'note': 'Suicide/self-harm search warning',
        'url': 'ytsearch1:i hate myself and i wanna die',
        'playlist_count': 1,
        'info_dict': {
            'id': 'i hate myself and i wanna die',
            'title': 'i hate myself and i wanna die',
        },
    }]


class YoutubeSearchDateIE(YoutubeTabBaseInfoExtractor, SearchInfoExtractor):
    IE_NAME = YoutubeSearchIE.IE_NAME + ':date'
    _SEARCH_KEY = 'ytsearchdate'
    IE_DESC = 'YouTube search, newest videos first'
    _SEARCH_PARAMS = 'CAISAhAB8AEB'  # Videos only, sorted by date
    _TESTS = [{
        'url': 'ytsearchdate5:youtube-dl test video',
        'playlist_count': 5,
        'info_dict': {
            'id': 'youtube-dl test video',
            'title': 'youtube-dl test video',
        },
    }]


class YoutubeSearchURLIE(YoutubeTabBaseInfoExtractor):
    IE_DESC = 'YouTube search URLs with sorting and filter support'
    IE_NAME = YoutubeSearchIE.IE_NAME + '_url'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/(?:results|search)\?([^#]+&)?(?:search_query|q)=(?:[^&]+)(?:[&#]|$)'
    _TESTS = [{
        'url': 'https://www.youtube.com/results?baz=bar&search_query=youtube-dl+test+video&filters=video&lclk=video',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'youtube-dl test video',
            'title': 'youtube-dl test video',
        },
    }, {
        'url': 'https://www.youtube.com/results?search_query=python&sp=EgIQAg%253D%253D',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'python',
            'title': 'python',
        },
    }, {
        'url': 'https://www.youtube.com/results?search_query=%23cats',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '#cats',
            'title': '#cats',
            # The test suite does not have support for nested playlists
            # 'entries': [{
            #     'url': r're:https://(www\.)?youtube\.com/hashtag/cats',
            #     'title': '#cats',
            # }],
        },
    }, {
        # Channel results
        'url': 'https://www.youtube.com/results?search_query=kurzgesagt&sp=EgIQAg%253D%253D',
        'info_dict': {
            'id': 'kurzgesagt',
            'title': 'kurzgesagt',
        },
        'playlist': [{
            'info_dict': {
                '_type': 'url',
                'id': 'UCsXVk37bltHxD1rDPwtNM8Q',
                'url': 'https://www.youtube.com/channel/UCsXVk37bltHxD1rDPwtNM8Q',
                'ie_key': 'YoutubeTab',
                'channel': 'Kurzgesagt – In a Nutshell',
                'description': 'md5:4ae48dfa9505ffc307dad26342d06bfc',
                'title': 'Kurzgesagt – In a Nutshell',
                'channel_id': 'UCsXVk37bltHxD1rDPwtNM8Q',
                # No longer available for search as it is set to the handle.
                # 'playlist_count': int,
                'channel_url': 'https://www.youtube.com/channel/UCsXVk37bltHxD1rDPwtNM8Q',
                'thumbnails': list,
                'uploader_id': '@kurzgesagt',
                'uploader_url': 'https://www.youtube.com/@kurzgesagt',
                'uploader': 'Kurzgesagt – In a Nutshell',
                'channel_is_verified': True,
                'channel_follower_count': int,
            },
        }],
        'params': {'extract_flat': True, 'playlist_items': '1'},
        'playlist_mincount': 1,
    }, {
        'url': 'https://www.youtube.com/results?q=test&sp=EgQIBBgB',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        qs = parse_qs(url)
        query = (qs.get('search_query') or qs.get('q'))[0]
        return self.playlist_result(self._search_results(query, qs.get('sp', (None,))[0]), query, query)


class YoutubeMusicSearchURLIE(YoutubeTabBaseInfoExtractor):
    IE_DESC = 'YouTube music search URLs with selectable sections, e.g. #songs'
    IE_NAME = 'youtube:music:search_url'
    _VALID_URL = r'https?://music\.youtube\.com/search\?([^#]+&)?(?:search_query|q)=(?:[^&]+)(?:[&#]|$)'
    _TESTS = [{
        'url': 'https://music.youtube.com/search?q=royalty+free+music',
        'playlist_count': 16,
        'info_dict': {
            'id': 'royalty free music',
            'title': 'royalty free music',
        },
    }, {
        'url': 'https://music.youtube.com/search?q=royalty+free+music&sp=EgWKAQIIAWoKEAoQAxAEEAkQBQ%3D%3D',
        'playlist_mincount': 30,
        'info_dict': {
            'id': 'royalty free music - songs',
            'title': 'royalty free music - songs',
        },
        'params': {'extract_flat': 'in_playlist'},
    }, {
        'url': 'https://music.youtube.com/search?q=royalty+free+music#community+playlists',
        'playlist_mincount': 30,
        'info_dict': {
            'id': 'royalty free music - community playlists',
            'title': 'royalty free music - community playlists',
        },
        'params': {'extract_flat': 'in_playlist'},
    }]

    _SECTIONS = {
        'albums': 'EgWKAQIYAWoKEAoQAxAEEAkQBQ==',
        'artists': 'EgWKAQIgAWoKEAoQAxAEEAkQBQ==',
        'community playlists': 'EgeKAQQoAEABagoQChADEAQQCRAF',
        'featured playlists': 'EgeKAQQoADgBagwQAxAJEAQQDhAKEAU==',
        'songs': 'EgWKAQIIAWoKEAoQAxAEEAkQBQ==',
        'videos': 'EgWKAQIQAWoKEAoQAxAEEAkQBQ==',
    }

    def _real_extract(self, url):
        qs = parse_qs(url)
        query = (qs.get('search_query') or qs.get('q'))[0]
        params = qs.get('sp', (None,))[0]
        if params:
            section = next((k for k, v in self._SECTIONS.items() if v == params), params)
        else:
            section = urllib.parse.unquote_plus(([*url.split('#'), ''])[1]).lower()
            params = self._SECTIONS.get(section)
            if not params:
                section = None
        title = join_nonempty(query, section, delim=' - ')
        return self.playlist_result(self._search_results(query, params, default_client='web_music'), title, title)
