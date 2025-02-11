from .common import InfoExtractor
from .nexx import NexxIE


class FunkIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|origin|play)\.)?funk\.net/(?:channel|playlist)/[^/?#]+/(?P<display_id>[0-9a-z-]+)-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.funk.net/channel/ba-793/die-lustigsten-instrumente-aus-dem-internet-teil-2-1155821',
        'md5': '8610449476156f338761a75391b0017d',
        'info_dict': {
            'id': '1155821',
            'ext': 'mp4',
            'title': 'Die LUSTIGSTEN INSTRUMENTE aus dem Internet - Teil 2',
            'description': 'md5:2a03b67596eda0d1b5125c299f45e953',
            'timestamp': 1514507395,
            'upload_date': '20171229',
            'duration': 426.0,
            'cast': ['United Creators PMB GmbH'],
            'thumbnail': 'https://assets.nexx.cloud/media/75/56/79/3YKUSJN1LACN0CRxL.jpg',
            'display_id': 'die-lustigsten-instrumente-aus-dem-internet-teil-2',
            'alt_title': 'Die LUSTIGSTEN INSTRUMENTE aus dem Internet Teil 2',
            'season_number': 0,
            'season': 'Season 0',
            'episode_number': 0,
            'episode': 'Episode 0',
        },
    }, {
        'url': 'https://www.funk.net/playlist/neuesteVideos/kameras-auf-dem-fusion-festival-1618699',
        'only_matching': True,
    }, {
        'url': 'https://play.funk.net/playlist/neuesteVideos/george-floyd-wenn-die-polizei-toetet-der-fall-2004391',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id, nexx_id = self._match_valid_url(url).groups()
        return {
            '_type': 'url_transparent',
            'url': f'nexx:741:{nexx_id}',
            'ie_key': NexxIE.ie_key(),
            'id': nexx_id,
            'display_id': display_id,
        }
