import functools
import re

from .common import InfoExtractor
from ..utils import float_or_none, int_or_none, smuggle_url, strip_or_none
from ..utils.traversal import traverse_obj


class TVAIE(InfoExtractor):
    _VALID_URL = r'https?://videos?\.tva\.ca/details/_(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://videos.tva.ca/details/_5596811470001',
        'info_dict': {
            'id': '5596811470001',
            'ext': 'mp4',
            'title': 'Un extrait de l\'épisode du dimanche 8 octobre 2017 !',
            'uploader_id': '5481942443001',
            'upload_date': '20171003',
            'timestamp': 1507064617,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'HTTP Error 404: Not Found',
    }, {
        'url': 'https://video.tva.ca/details/_5596811470001',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/5481942443001/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % video_id, {'geo_countries': ['CA']}),
            'ie_key': 'BrightcoveNew',
        }


class QubIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?qub\.ca/(?:[^/]+/)*[0-9a-z-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.qub.ca/tvaplus/tva/alerte-amber/saison-1/episode-01-1000036619',
        'md5': '949490fd0e7aee11d0543777611fbd53',
        'info_dict': {
            'id': '6084352463001',
            'ext': 'mp4',
            'title': 'Ép 01. Mon dernier jour',
            'uploader_id': '5481942443001',
            'upload_date': '20190907',
            'timestamp': 1567899756,
            'description': 'md5:9c0d7fbb90939420c651fd977df90145',
            'thumbnail': r're:https://.+\.jpg',
            'episode': 'Ép 01. Mon dernier jour',
            'episode_number': 1,
            'tags': ['alerte amber', 'alerte amber saison 1', 'surdemande'],
            'duration': 2625.963,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'Alerte Amber',
            'channel': 'TVA',
        },
    }, {
        'url': 'https://www.qub.ca/tele/video/lcn-ca-vous-regarde-rev-30s-ap369664-1009357943',
        'only_matching': True,
    }]
    # reference_id also works with old account_id(5481942443001)
    # BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/5813221784001/default_default/index.html?videoId=ref:%s'

    def _real_extract(self, url):
        entity_id = self._match_id(url)
        webpage = self._download_webpage(url, entity_id)
        entity = self._search_nextjs_data(webpage, entity_id)['props']['initialProps']['pageProps']['fallbackData']
        video_id = entity['videoId']
        episode = strip_or_none(entity.get('name'))

        return {
            '_type': 'url_transparent',
            'url': f'https://videos.tva.ca/details/_{video_id}',
            'ie_key': TVAIE.ie_key(),
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
