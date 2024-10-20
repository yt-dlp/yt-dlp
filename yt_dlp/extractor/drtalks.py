from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import extract_attributes, smuggle_url


class DrTalksIE(InfoExtractor):
    _VALID_URL = r'https?://event\.drtalks\.com/(?P<id>.+/[^/]+)/?'

    _TESTS = [{
        'url': 'https://event.drtalks.com/reversing-heart-disease-summit/free-access-day-1',
        'info_dict': {
            'id': '1758074870279626053',
            'title': 'Free Access Day 1 - Events at DrTalks',
            'thumbnail': r're:https://event.drtalks.com/wp-content/uploads/.+',
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
            'thumbnail': r're:https://event.drtalks.com/wp-content/uploads/.+',
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
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_%s/index.html?playlistId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_attrs = extract_attributes(self._search_regex(
            r'(<video-js[^>]+\bid=(["\'])myPlayerID\2[^>]*>)', webpage, 'player'))
        bc_url = smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % (
            player_attrs.get('data-account', '6314452011001'),
            player_attrs.get('data-player', 'f3rfrCUjm'),
            player_attrs.get('data-embed', 'default'),
            player_attrs['data-playlist-id']), {'source_url': url})

        return self.url_result(
            bc_url, BrightcoveNewIE.ie_key(), video_id, self._og_search_title(webpage),
            url_transparent=True, thumbnail=self._og_search_thumbnail(webpage))
