from .common import InfoExtractor
from ..utils import (
    MEDIA_EXTENSIONS,
    ExtractorError,
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

        api_url = f'{self._API_BASE}/episodes/{display_id}'
        self.write_debug(f'API URL: {api_url}')

        api_data = self._download_json(
            api_url, display_id,
            note='Downloading episode data from API',
        )

        self.write_debug(f'API response keys: {list(api_data.keys()) if api_data else None}')

        entry = traverse_obj(api_data, ('entry',))
        if not entry:
            raise ExtractorError('Could not extract episode data from API response')

        return self._parse_entry(entry)


class RinseFMArtistPlaylistIE(RinseFMBaseIE):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/shows/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/shows/resources/',
        'info_dict': {
            'id': 'resources',
            'title': '[re]sources',
            'description': '[re]sources est un label parisien piloté par le DJ et producteur Tommy Kid.',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://rinse.fm/shows/ivy/',
        'info_dict': {
            'id': 'ivy',
            'title': '[IVY]',
            'description': 'A dedicated space for DNB/Turbo House and 4x4.',
        },
        'playlist_mincount': 7,
    }]

    def _entries(self, episodes):
        for episode in episodes or []:
            # Filter out episodes without valid file URLs
            file_url = episode.get('fileUrl')
            if file_url and determine_ext(file_url) in MEDIA_EXTENSIONS.audio:
                yield self._parse_entry(episode)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        api_url = f'{self._API_BASE}/shows/{playlist_id}'
        self.write_debug(f'API URL: {api_url}')

        api_data = self._download_json(
            api_url, playlist_id,
            note='Downloading show data from API',
        )

        self.write_debug(f'API response keys: {list(api_data.keys()) if api_data else None}')

        show_entry = traverse_obj(api_data, ('entry',))
        episodes = traverse_obj(api_data, ('episodes',))

        self.write_debug(f'Found {len(episodes) if episodes else 0} episodes')

        if not episodes:
            raise ExtractorError('Could not extract episodes from API response')

        title = traverse_obj(show_entry, ('title', {str}))
        description = traverse_obj(show_entry, ('extract', {str}))

        return self.playlist_result(
            self._entries(episodes), playlist_id, title, description=description,
        )
