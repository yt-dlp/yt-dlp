import functools

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class ReverbNationIE(InfoExtractor):
    IE_NAME = 'reverbnation:song'
    _VALID_URL = r'https?://(?:www\.)?reverbnation\.com/.*?/song/(?P<id>\d+).*?$'
    _TESTS = [{
        'url': 'http://www.reverbnation.com/alkilados/song/16965047-mona-lisa',
        'md5': 'c0aaf339bcee189495fdf5a8c8ba8645',
        'info_dict': {
            'id': '16965047',
            'ext': 'mp3',
            'vcodec': 'none',
            'tbr': 192,
            'duration': 217,
            'title': 'MONA LISA',
            'artists': ['ALKILADOS'],
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }]

    def _extract_song(self, json_data):
        return {
            'ext': 'mp3',
            'vcodec': 'none',
            **traverse_obj(json_data, {
                'id': ('id', {str_or_none}),
                'title': ('name', {str}),
                'artists': ('artist', 'name', all),
                'thumbnail': ('image', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'tbr': ('bitrate', {int_or_none}),
                'url': ('url', {url_or_none}),
            }),
        }

    def _real_extract(self, url):
        song_id = self._match_id(url)

        api_res = self._download_json(
            f'https://api.reverbnation.com/song/{song_id}',
            song_id,
            note=f'Downloading information of song {song_id}',
        )

        return self._extract_song(api_res)


class ReverbNationArtistIE(ReverbNationIE):
    IE_NAME = 'reverbnation:artist'
    _VALID_URL = r'https?://(?:www\.)?reverbnation\.com/(?P<id>[\w-]+)(?:/songs)?$'
    _TESTS = [{
        'url': 'https://www.reverbnation.com/morganandersson',
        'info_dict': {
            'id': '1078497',
            'title': 'morganandersson',
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://www.reverbnation.com/monogem/songs',
        'info_dict': {
            'id': '3716672',
            'title': 'monogem',
        },
        'playlist_mincount': 10,
    }]
    _PAGE_SIZE = 25

    def _entries(self, artist_id, page):
        page_data = self._download_json(
            f'https://www.reverbnation.com/api/artist/{artist_id}/songs',
            f'{artist_id}_{page + 1}', query={'page': page + 1, 'per_page': self._PAGE_SIZE})
        for song_data in page_data['results']:
            yield self._extract_song(song_data)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        artist_url = self._html_search_meta('twitter:player', webpage, 'player url')
        artist_id = self._search_regex(r'artist_(?P<artist>\d+)', artist_url, 'artist id')
        page_data = self._search_json('"SONGS_WITH_PAGINATION":', webpage, 'json_data', display_id)
        total_pages = traverse_obj(page_data, ('pagination', 'page_count', {int}))
        self._PAGE_SIZE = traverse_obj(page_data, ('pagination', 'per_page', {int}))

        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, artist_id),
            total_pages, self._PAGE_SIZE), artist_id, display_id)
