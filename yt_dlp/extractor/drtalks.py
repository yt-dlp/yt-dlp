import functools
import urllib.parse

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import extract_attributes


class DrTalksIE(InfoExtractor):
    _VALID_URL = r'https?://event\.drtalks\.com/(?P<id>.+/[^/]+)/?'

    _TESTS = [{
        'url': 'https://event.drtalks.com/reversing-heart-disease-summit/free-access-day-1',
        'info_dict': {
            'id': '1758074870279626053',
            'title': 'Free Access Day 1 - Events at DrTalks',
            'thumbnail': 're:https://event.drtalks.com/wp-content/uploads/.+',
        },
        'playlist_mincount': 11,
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://event.drtalks.com/bioenergetics-2022/free-access-day-1/',
        'info_dict': {
            'id': '1747611460188466596',
            'title': 'The BioEnergetics Summit',
            'thumbnail': 're:https://event.drtalks.com/wp-content/uploads/.+',
        },
        'playlist_mincount': 8,
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://event.drtalks.com/mitochondrial-summit/encore-access-day-6',
        'only_matching': True,
    }, {
        'url': 'https://event.drtalks.com/medicine-of-mindset-summit/free-access-day-1/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_attrs = extract_attributes(self._search_regex(r'(<video-js[^>]+>)', webpage, 'player'))

        playlist_url = functools.reduce(urllib.parse.urljoin, [
            'https://players.brightcove.net/',
            f'{player_attrs["data-account"]}/',
            f'{player_attrs["data-player"]}_{player_attrs["data-embed"]}/',
            f'index.html?playlistId={player_attrs["data-playlist-id"]}',
        ])

        return self.url_result(
            playlist_url, BrightcoveNewIE.ie_key(), video_id, self._og_search_title(webpage),
            url_transparent=True, thumbnail=self._og_search_thumbnail(webpage))
