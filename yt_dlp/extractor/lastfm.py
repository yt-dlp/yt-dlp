# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none
)


class LastFMPlaylistBaseIE(InfoExtractor):
    def _extract_current_page(self, url):
        return int_or_none(self._search_regex(
            r'\bpage=(\d+)', url, 'page', default=None))

    def _extract_last_page(self, webpage):
        last_page = None
        pagination_list = self._search_regex(
            r'(?s)class="[^"]*pagination-list[^"]*"[^>]*>(.+?)</ul>', webpage, 'pagination_list', fatal=False,
            default=None)

        if pagination_list:
            page_numbers = re.findall(r'(\d+)', pagination_list)
            last_page = max([int_or_none(page_number) for page_number in page_numbers])

        return last_page

    def _extract_entries(self, webpage):
        tbody = self._search_regex(
            r'(?s)tbody\s+data-playlisting-add-entries[^>]*>(.+?)</tbody>', webpage, 'tbody')
        return [
            self.url_result(player_url, 'Youtube')
            for player_url in re.findall(r'href="([^"]+youtube.com/watch[^"]+)"', tbody)
        ]

    def _download_page(self, url, current_page_number, last_page_number, playlist_id):
        note = 'Downloading page'
        query = {}

        if last_page_number:
            note = '%s %d of %d' % (note, current_page_number, last_page_number)
            query['page'] = current_page_number

        return self._download_webpage(url, playlist_id, note, query=query)

    def _entries(self, url, playlist_id):
        webpage = self._download_webpage(url, playlist_id)
        current_page_number = self._extract_current_page(url)
        last_page_number = self._extract_last_page(webpage)
        start_page_number = current_page_number or 1
        end_page_number = last_page_number if last_page_number is not None else start_page_number

        for page_number in range(start_page_number, end_page_number + 1):
            webpage = self._download_page(url, page_number, last_page_number, playlist_id)
            page_entries = self._extract_entries(webpage)

            for e in page_entries:
                yield e

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        return self.playlist_result(self._entries(url, playlist_id), playlist_id)


class LastFMAlbumIE(LastFMPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/music/(?P<artist_id>[^/]+)/(?P<id>[^+/#?][^/#?]+)(/|[^/]*/?)$'
    _TESTS = [{
        'url': 'https://www.last.fm/music/Oasis/(What%27s+the+Story)+Morning+Glory%3F',
        'info_dict': {
            'id': '(What%27s+the+Story)+Morning+Glory%3F',
        },
        'playlist_count': 12,
    }]


class LastFMPlaylistIE(LastFMPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/(music|tag)/(?P<id>[^/#?]+)(/|/\+?tracks/?|[^/]*/?)$'
    _TESTS = [{
        'url': 'https://www.last.fm/music/Oasis',
        'info_dict': {
            'id': 'Oasis',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://www.last.fm/music/Oasis/+tracks',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/tag/rock',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/tag/rock/tracks',
        'only_matching': True,
    }]


class LastFMIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://(?:www\.)?last\.fm/
                    music/(?P<artist_id>[^/]+)/(?P<album_id>[^/]+)/(?P<id>[^/#?]+)(/|[^/]*/?)$
                  '''
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
        'url': 'https://www.last.fm/music/Oasis/_/Don%27t+Look+Back+In+Anger+-+Remastered',
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
