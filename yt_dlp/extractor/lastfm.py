import re

from .common import InfoExtractor
from ..utils import int_or_none


class LastFMPlaylistBaseIE(InfoExtractor):
    def _entries(self, url, playlist_id):
        page_number = int_or_none(self._search_regex(r'\bpage=(\d+)', url, 'page', default=None))
        webpage = self._download_webpage(url, playlist_id, note=f'Downloading page {page_number if page_number else 1}')
        page_entries = self._extract_webpage(webpage)
        if not page_number:
            page_number = 2
            while page_number:
                webpage = self._download_webpage(
                    url, playlist_id,
                    note=f'Downloading page {page_number}',
                    query={'page': page_number})
                page_number = int_or_none(self._search_regex(
                    r'<li.+class=\"pagination-next\".+data-pagination-next-link\>[^<]*\<a.+href=\".*page=(\d+)',
                    webpage,
                    'last_page', default=None))
                page_entries.extend(self._extract_webpage(webpage))
        for e in page_entries:
            yield e

    def _extract_webpage(self, webpage):
        return [
            self.url_result(player_url, 'Youtube')
            for player_url in set(re.findall(r'data-youtube-url="([^"]+)"', webpage))
        ]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        return self.playlist_result(self._entries(url, playlist_id), playlist_id)


class LastFMPlaylistIE(LastFMPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/(music|tag)/(?P<id>[^/]+)(?:/[^/]+)?/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.last.fm/music/Oasis/(What%27s+the+Story)+Morning+Glory%3F',
        'info_dict': {
            'id': 'Oasis',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://www.last.fm/music/Oasis',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis?top_tracks_date_preset=ALL#top-tracks',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/+tracks',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/+tracks?page=2',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/+tracks?date_preset=LAST_90_DAYS#top-tracks',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/tag/rock',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/tag/rock/tracks',
        'only_matching': True,
    }]


class LastFMUserIE(LastFMPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/user/[^/]+/playlists/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.last.fm/user/mehq/playlists/12319471',
        'info_dict': {
            'id': '12319471',
        },
        'playlist_count': 30,
    }, {
        'url': 'https://www.last.fm/user/naamloos1/playlists/12543760',
        'info_dict': {
            'id': '12543760',
        },
        'playlist_mincount': 80,
    }, {
        'url': 'https://www.last.fm/user/naamloos1/playlists/12543760?page=3',
        'info_dict': {
            'id': '12543760',
        },
        'playlist_mincount': 30,
    }]


class LastFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/music(?:/[^/]+){2}/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.last.fm/music/Oasis/_/Wonderwall',
        'md5': '9c4a70c2e84c03d54fe24229b9e13b7b',
        'info_dict': {
            'id': '6hzrDeceEKc',
            'ext': 'mp4',
            'title': 'Oasis - Wonderwall  (Official Video)',
            'thumbnail': r're:^https?://i.ytimg.com/.*\.jpg$',
            'description': 'md5:0848669853c10687cc28e88b5756738f',
            'uploader': 'Oasis',
            'uploader_id': 'oasisinetofficial',
            'upload_date': '20080207',
            'album': '(What\'s The Story) Morning Glory? (Remastered)',
            'track': 'Wonderwall (Remastered)',
            'channel_id': 'UCUDVBtnOQi4c7E8jebpjc9Q',
            'view_count': int,
            'live_status': 'not_live',
            'channel_url': 'https://www.youtube.com/channel/UCUDVBtnOQi4c7E8jebpjc9Q',
            'tags': 'count:39',
            'creator': 'Oasis',
            'uploader_url': 're:^https?://www.youtube.com/user/oasisinetofficial',
            'duration': 279,
            'alt_title': 'Wonderwall (Remastered)',
            'age_limit': 0,
            'channel': 'Oasis',
            'channel_follower_count': int,
            'categories': ['Music'],
            'availability': 'public',
            'like_count': int,
            'playable_in_embed': True,
            'artist': 'Oasis',
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'https://www.last.fm/music/Oasis/_/Don%27t+Look+Back+In+Anger+-+Remastered/',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Guns+N%27+Roses/_/Sweet+Child+o%27+Mine',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_url = self._search_regex(r'(?s)class="header-new-playlink"\s+href="([^"]+)"', webpage, 'player_url')
        return self.url_result(player_url, 'Youtube')
