import functools

from .common import InfoExtractor
from ..utils import InAdvancePagedList, float_or_none, int_or_none, qualities, str_or_none, traverse_obj, url_or_none


class ReverbNationIE(InfoExtractor):
    IE_NAME = 'reverbnation:song'
    _VALID_URL = r'https?://(?:www\.)?reverbnation\.com/.*?/song/(?P<id>\d+).*?$'
    _TESTS = [{
        'url': 'http://www.reverbnation.com/alkilados/song/16965047-mona-lisa',
        'md5': 'c0aaf339bcee189495fdf5a8c8ba8645',
        'info_dict': {
            'id': '16965047',
            'ext': 'mp3',
            'tbr': 192,
            'duration': 217,
            'title': 'MONA LISA',
            'uploader': 'ALKILADOS',
            'uploader_id': '216429',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }]

    def _real_extract(self, url):
        song_id = self._match_id(url)

        api_res = self._download_json(
            f'https://api.reverbnation.com/song/{song_id}',
            song_id,
            note=f'Downloading information of song {song_id}',
        )

        THUMBNAILS = ('thumbnail', 'image')
        quality = qualities(THUMBNAILS)
        thumbnails = []
        for thumb_key in THUMBNAILS:
            if api_res.get(thumb_key):
                thumbnails.append({
                    'url': api_res[thumb_key],
                    'preference': quality(thumb_key),
                })

        return {
            'id': str_or_none(song_id),
            'ext': 'mp3',
            'vcodec': 'none',
            'thumbnails': thumbnails,
            **traverse_obj(api_res, {
                'title': ('name', {str_or_none}),
                'url': ('url', {url_or_none}),
                'uploader': ('artist', 'name', {str_or_none}),
                'uploader_id': ('artist', 'id', {str_or_none}),
                'duration': ('duration', {float_or_none}),
                'tbr': ('bitrate', {int_or_none}),
            }),
        }


class ReverbNationArtistIE(InfoExtractor):
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

    def _yield_songs(self, json_data):
        for song in json_data.get('results'):
            yield {
                'ext': 'mp3',
                'vcodec': 'none',
                **traverse_obj(song, {
                    'id': ('id', {str_or_none}),
                    'title': ('name', {str_or_none}),
                    'url': ('url', {url_or_none}),
                    'uploader': ('artist', 'name', {str_or_none}),
                    'uploader_id': ('artist', 'id', {str_or_none}),
                    'duration': ('duration', {float_or_none}),
                    'tbr': ('bitrate', {int_or_none}),
                    'thumbnail': ('thumbnail', {url_or_none}),
                }),
            }

    def _fetch_page(self, artist_id, page):
        return self._download_json(f'https://www.reverbnation.com/api/artist/{artist_id}/songs?page={page}&per_page={self._PAGE_SIZE}', f'{artist_id}_{page}')

    def _entries(self, token, first_page_data, page):
        page_data = first_page_data if not page else self._fetch_page(token, page + 1)
        yield from self._yield_songs(page_data)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        artist_url = self._html_search_meta('twitter:player', webpage, 'player url')
        artist_id = self._search_regex(r'artist_(?P<artist>\d+)', artist_url, 'artist id')
        playlist_data = self._fetch_page(artist_id, 1)
        total_pages = traverse_obj(playlist_data, ('pagination', 'page_count', {int}))

        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, artist_id, playlist_data),
            total_pages, self._PAGE_SIZE), artist_id, display_id)
