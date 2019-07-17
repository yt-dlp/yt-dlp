# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..compat import compat_urlparse


class TelevizeSeznamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?televizeseznam\.cz/video/.+/(?P<id>.+)'

    _API_BASE = 'https://www.televizeseznam.cz'
    _GRAPHQL_URL = '%s/api/graphql' % _API_BASE
    _GRAPHQL_QUERY = '''query LoadEpisode($urlName : String){ episode(urlName: $urlName){ ...VideoDetailFragmentOnEpisode } }
		fragment VideoDetailFragmentOnEpisode on Episode {
			id
			spl
			urlName
			name
			perex
		}
'''

    _TEST = {
        'url': 'https://www.televizeseznam.cz/video/lajna/buh-57953890',
        'md5': '40c41ade1464a390a0b447e333df4239',
        'info_dict': {
            'id': 'buh-57953890',
            'title': 'Bůh',
            'description': 'Trenér Hrouzek je plný rozporů. Na pomoc si povolá i toho nejvyššího. Kdo to ale je? Pomůže mu vyřešit několik dilemat, která se mu v poslední době v životě nahromadila?',
            'ext': 'mp4',
        }
    }

    def extract_subtitles(self, spl_url, play_list):

        if not play_list:
            return None

        subtitles = {}
        for k, v in play_list.items():
            subtitles.update({
                v['language']: {
                    'ext': 'srt',
                    'url': compat_urlparse.urljoin(spl_url, v['urls']['srt'])
                }
            })
        return subtitles

    def extract_formats(self, spl_url, play_list, subtitles):
        formats = []
        for r, v in play_list.items():
            formats.append({
                'url': compat_urlparse.urljoin(spl_url, v['url']),
                'width': v['resolution'][0],
                'height': v['resolution'][1],
                'resolution': '%sx%s' % (v['resolution'][0], v['resolution'][1]),
                'protocol': 'https',
                'ext': 'mp4',
                'subtitles': subtitles,
            })
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            self._GRAPHQL_URL, video_id, 'Downloading GraphQL result',
            data=json.dumps({
                'query': self._GRAPHQL_QUERY,
                'variables': {'urlName': video_id}
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json;charset=UTF-8'}
        )['data']

        spl_url = data['episode']['spl']
        play_list = self._download_json(spl_url + 'spl2,3', video_id, 'Downloading playlist')['data']
        subtitles = self.extract_subtitles(spl_url, play_list.get('subtitles'))
        formats = self.extract_formats(spl_url, play_list['mp4'], subtitles)

        return {
            'id': video_id,
            'title': data['episode'].get('name'),
            'description': data['episode'].get('perex'),
            'formats': formats
        }
