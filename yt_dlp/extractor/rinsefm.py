from .common import InfoExtractor
from ..utils import (
    MEDIA_EXTENSIONS,
    determine_ext,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class RinseFMBaseIE(InfoExtractor):
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
            'release_date': '20231215'
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        entry = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['entry']

        return self._parse_entry(entry)


class RinseFMArtistPlaylistIE(RinseFMBaseIE):
    _VALID_URL = r'https?://(?:www\.)?rinse\.fm/shows/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://rinse.fm/shows/resources/',
        'info_dict': {
            'id': 'resources',
            'title': '[re]sources',
            'description': '[re]sources est un label parisien piloté par le DJ et producteur Tommy Kid.'
        },
        'playlist_mincount': 40
    }, {
        'url': 'https://rinse.fm/shows/ivy/',
        'info_dict': {
            'id': 'ivy',
            'title': '[IVY]',
            'description': 'A dedicated space for DNB/Turbo House and 4x4.'
        },
        'playlist_mincount': 7
    }]

    def _entries(self, data):
        for episode in traverse_obj(data, (
            'props', 'pageProps', 'episodes', lambda _, v: determine_ext(v['fileUrl']) in MEDIA_EXTENSIONS.audio)
        ):
            yield self._parse_entry(episode)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        title = self._og_search_title(webpage) or self._html_search_meta('title', webpage)
        description = self._og_search_description(webpage) or self._html_search_meta(
            'description', webpage)
        data = self._search_nextjs_data(webpage, playlist_id)

        return self.playlist_result(
            self._entries(data), playlist_id, title, description=description)
