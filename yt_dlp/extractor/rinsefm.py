from .common import InfoExtractor
from ..utils import (
    MEDIA_EXTENSIONS,
    determine_ext,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class RinseFMBaseIE(InfoExtractor):
    _API_BASE = 'https://rinse.fm/api/query/v1'

    @staticmethod
    def _parse_entry(entry):
        return {
            **traverse_obj(entry, {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'url': ('fileUrl', {url_or_none}),
                'release_timestamp': ('episodeDate', {parse_iso8601}),
                'thumbnail': ('featuredImage', 0, 'filename', {str},
                              {lambda x: x and f'https://rinse.imgix.net/media/{x}'}),
                'webpage_url': ('slug', {str},
                                {lambda x: x and f'https://rinse.fm/episodes/{x}'}),
            }),
            'vcodec': 'none',
            'extractor_key': RinseFMIE.ie_key(),
            'extractor': RinseFMIE.IE_NAME,
        }


class RinseFMIE(RinseFMBaseIE):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/episodes/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/episodes/club-glow-15-12-2023-2000/',
        'md5': '76ee0b719315617df42e15e710f46c7b',
        'info_dict': {
            'id': '1536535',
            'ext': 'mp3',
            'title': 'Club Glow - 15/12/2023 - 20:00',
            'thumbnail': r're:^https://.+\.(?:jpg|JPG)$',
            'release_timestamp': 1702598400,
            'release_date': '20231215',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        entry = self._download_json(
            f'{self._API_BASE}/episodes/{display_id}', display_id,
            note='Downloading episode data from API')['entry']

        return self._parse_entry(entry)


class RinseFMArtistPlaylistIE(RinseFMBaseIE):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/shows/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/shows/resources/',
        'info_dict': {
            'id': 'resources',
            'title': '[re]sources',
            'description': 'md5:fd6a7254e8273510e6d49fbf50edf392',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://www.rinse.fm/shows/esk',
        'info_dict': {
            'id': 'esk',
            'title': 'Esk',
            'description': 'md5:5893d7c1d411ae8dea7fba12f109aa98',
        },
        'playlist_mincount': 139,
    }]

    def _entries(self, data):
        for episode in traverse_obj(data, (
            'episodes', lambda _, v: determine_ext(v['fileUrl']) in MEDIA_EXTENSIONS.audio),
        ):
            yield self._parse_entry(episode)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        api_data = self._download_json(
            f'{self._API_BASE}/shows/{playlist_id}', playlist_id,
            note='Downloading show data from API')

        return self.playlist_result(
            self._entries(api_data), playlist_id,
            **traverse_obj(api_data, ('entry', {
                'title': ('title', {str}),
                'description': ('description', {str}),
            })))
