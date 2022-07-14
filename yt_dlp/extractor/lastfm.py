import re

from .common import InfoExtractor
from ..utils import int_or_none, format_field


class LastFMPlaylistBaseIE(InfoExtractor):
    def _entries(self, url, playlist_id):
        webpage = self._download_webpage(url, playlist_id)
        start_page_number = int_or_none(self._search_regex(
            r'\bpage=(\d+)', url, 'page', default=None)) or 1
        last_page_number = int_or_none(self._search_regex(
            r'>(\d+)</a>[^<]*</li>[^<]*<li[^>]+class="pagination-next', webpage, 'last_page', default=None))

        for page_number in range(start_page_number, (last_page_number or start_page_number) + 1):
            webpage = self._download_webpage(
                url, playlist_id,
                note='Downloading page %d%s' % (page_number, format_field(last_page_number, None, ' of %d')),
                query={'page': page_number})
            page_entries = [
                self.url_result(player_url, 'Youtube')
                for player_url in set(re.findall(r'data-youtube-url="([^"]+)"', webpage))
            ]

            for e in page_entries:
                yield e

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
        'playlist_count': 11,
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
