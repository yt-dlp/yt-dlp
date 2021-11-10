# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..utils import urljoin


class TelevizeSeznamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:stream|televizeseznam)\.cz/.+/(?P<display_id>.+)-(?P<id>[0-9]+)'

    _GRAPHQL_URL = 'https://www.televizeseznam.cz/api/graphql'
    _GRAPHQL_QUERY = '''query LoadEpisode($urlName : String){ episode(urlName: $urlName){ ...VideoDetailFragmentOnEpisode } }
        fragment VideoDetailFragmentOnEpisode on Episode {
            id
            spl
            urlName
            name
            perex
        }
'''

    _TESTS = [{
        'url': 'https://www.televizeseznam.cz/video/lajna/buh-57953890',
        'md5': '40c41ade1464a390a0b447e333df4239',
        'info_dict': {
            'id': '57953890',
            'display_id': 'buh',
            'title': 'Bůh',
            'description': 'Trenér Hrouzek je plný rozporů. Na pomoc si povolá i toho nejvyššího. Kdo to ale je? Pomůže mu vyřešit několik dilemat, která se mu v poslední době v životě nahromadila?',
            'ext': 'mp4',
        }
    }, {
        'url': 'https://www.stream.cz/tajemno/znicehonic-jim-skrz-strechu-prolitnul-zahadny-predmet-badatele-vse-objasnili-64147267',
        'md5': '3ee4d0be040e8f4a543e67e509d55e3f',
        'info_dict': {
            'id': '64147267',
            'display_id': 'znicehonic-jim-skrz-strechu-prolitnul-zahadny-predmet-badatele-vse-objasnili',
            'title': 'Zničehonic jim skrz střechu prolítnul záhadný předmět. Badatelé vše objasnili',
            'description': "18. listopadu 2010 spadl na jeden z domů v Ohrazenicích na Třebíčsku kus ledu. Badatelé si potom marně lámali hlavu nad tím, kde se mohl vzít. Kus ledu napáchal v domě nemalou škodu, naštěstí jen materiální, nikoho neporanil.\r\n",
            'ext': 'mp4',
        }
    }]

    def extract_subtitles(self, spl_url, play_list):

        if not play_list:
            return None

        subtitles = {}
        for k, v in play_list.items():
            if v.get('language'):
                for ext in v.get('urls'):
                    subtitles.setdefault(v['language'], []).append({
                        'ext': ext,
                        'url': urljoin(spl_url, v['urls'].get(ext))
                    })
        return subtitles

    def _extract(self, ext, spl_url, play_list):
        formats = []
        for r, v in play_list.items():
            format = {
                'format_id': r,
                'url': urljoin(spl_url, v.get('url')),
                'protocol': 'https',
                'ext': ext
            }
            if v.get('resolution'):
                format.update({'width': v['resolution'][0], 'height': v['resolution'][1]})

            formats.append(format)
        return formats

    def extract_formats(self, spl_url, play_list):
        formats = []

        if play_list.get('http_stream') and play_list['http_stream'].get('qualities'):
            formats.extend(self._extract(None, spl_url, play_list['http_stream']['qualities']))

        if play_list.get('mp4'):
            formats.extend(self._extract('mp4', spl_url, play_list['mp4']))

        self._sort_formats(formats)
        return formats

    def _real_extract(self, url):
        display_id, video_id = re.match(self._VALID_URL, url).groups()

        data = self._download_json(
            self._GRAPHQL_URL, video_id, 'Downloading GraphQL result',
            data=json.dumps({
                'query': self._GRAPHQL_QUERY,
                'variables': {'urlName': video_id}
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json;charset=UTF-8'}
        )['data']

        spl_url = data['episode']['spl'] + 'spl2,3'
        metadata = self._download_json(spl_url, video_id, 'Downloading playlist')
        if 'Location' in metadata and 'data' not in metadata:
            # they sometimes wants to redirect
            spl_url = metadata['Location']
            metadata = self._download_json(spl_url, video_id, 'Redirected -> Downloading playlist')
        play_list = metadata['data']

        return {
            'id': video_id,
            'display_id': display_id,
            'title': data['episode'].get('name'),
            'description': data['episode'].get('perex'),
            'subtitles': self.extract_subtitles(spl_url, play_list.get('subtitles')),
            'formats': self.extract_formats(spl_url, play_list)
        }
