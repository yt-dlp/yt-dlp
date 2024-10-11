import functools
import re

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import float_or_none, int_or_none, smuggle_url, strip_or_none
from ..utils.traversal import traverse_obj


class TVAIE(InfoExtractor):
    IE_NAME = 'tvaplus'
    IE_DESC = 'TVA+'
    _VALID_URL = r'https?://(?:www\.)?tvaplus\.ca/(?:[^/?#]+/)*[\w-]+-(?P<id>\d+)(?:$|[#?])'
    _TESTS = [{
        'url': 'https://www.tvaplus.ca/tva/alerte-amber/saison-1/episode-01-1000036619',
        'md5': '949490fd0e7aee11d0543777611fbd53',
        'info_dict': {
            'id': '6084352463001',
            'ext': 'mp4',
            'title': 'Mon dernier jour',
            'uploader_id': '5481942443001',
            'upload_date': '20190907',
            'timestamp': 1567899756,
            'description': 'md5:9c0d7fbb90939420c651fd977df90145',
            'thumbnail': r're:https://.+\.jpg',
            'episode': 'Mon dernier jour',
            'episode_number': 1,
            'tags': ['alerte amber', 'alerte amber saison 1', 'surdemande'],
            'duration': 2625.963,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'Alerte Amber',
            'channel': 'TVA',
        },
    }, {
        'url': 'https://www.tvaplus.ca/tva/le-baiser-du-barbu/le-baiser-du-barbu-886644190',
        'info_dict': {
            'id': '6354448043112',
            'ext': 'mp4',
            'title': 'Le Baiser du barbu',
            'uploader_id': '5481942443001',
            'upload_date': '20240606',
            'timestamp': 1717694023,
            'description': 'md5:025b1219086c1cbf4bc27e4e034e8b57',
            'thumbnail': r're:https://.+\.jpg',
            'episode': 'Le Baiser du barbu',
            'tags': ['fullepisode', 'films'],
            'duration': 6053.504,
            'series': 'Le Baiser du barbu',
            'channel': 'TVA',
        },
    }]
    _BC_URL_TMPL = 'https://players.brightcove.net/5481942443001/default_default/index.html?videoId={}'

    def _real_extract(self, url):
        entity_id = self._match_id(url)
        webpage = self._download_webpage(url, entity_id)
        entity = self._search_nextjs_data(webpage, entity_id)['props']['pageProps']['staticEntity']
        video_id = entity['videoId']
        episode = strip_or_none(entity.get('name'))

        return {
            '_type': 'url_transparent',
            'url': smuggle_url(self._BC_URL_TMPL.format(video_id), {'geo_countries': ['CA']}),
            'ie_key': BrightcoveNewIE.ie_key(),
            'id': video_id,
            'title': episode,
            'episode': episode,
            **traverse_obj(entity, {
                'description': ('longDescription', {str}),
                'duration': ('durationMillis', {functools.partial(float_or_none, scale=1000)}),
                'channel': ('knownEntities', 'channel', 'name', {str}),
                'series': ('knownEntities', 'videoShow', 'name', {str}),
                'season_number': ('slug', {lambda x: re.search(r'/s(?:ai|ea)son-(\d+)/', x)}, 1, {int_or_none}),
                'episode_number': ('episodeNumber', {int_or_none}),
            }),
        }
