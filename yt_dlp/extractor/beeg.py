from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    int_or_none,
    traverse_obj,
    unified_timestamp,
)


class BeegIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?beeg\.(?:com(?:/video)?)/-?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://beeg.com/-0983946056129650',
        'md5': '51d235147c4627cfce884f844293ff88',
        'info_dict': {
            'id': '0983946056129650',
            'ext': 'mp4',
            'title': 'sucked cock and fucked in a private plane',
            'duration': 927,
            'tags': list,
            'age_limit': 18,
            'upload_date': '20220117',
            'timestamp': 1642406589,
            'display_id': 2540839,
        }
    }, {
        'url': 'https://beeg.com/-0599050563103750?t=4-861',
        'md5': 'bd8b5ea75134f7f07fad63008db2060e',
        'info_dict': {
            'id': '0599050563103750',
            'ext': 'mp4',
            'title': 'Bad Relatives',
            'duration': 2060,
            'tags': list,
            'age_limit': 18,
            'description': 'md5:b4fc879a58ae6c604f8f259155b7e3b9',
            'timestamp': 1643623200,
            'display_id': 2569965,
            'upload_date': '20220131',
        }
    }, {
        # api/v6 v2
        'url': 'https://beeg.com/1941093077?t=911-1391',
        'only_matching': True,
    }, {
        # api/v6 v2 w/o t
        'url': 'https://beeg.com/1277207756',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video = self._download_json(
            'https://store.externulls.com/facts/file/%s' % video_id,
            video_id, 'Downloading JSON for %s' % video_id)

        fc_facts = video.get('fc_facts')
        firstKey = None
        for i in range(len(fc_facts)):
            if not firstKey or fc_facts[i - 1]['id'] < fc_facts[firstKey]['id']:
                firstKey = i - 1

        resources = traverse_obj(video, ('file', 'hls_resources'), ('fc_facts', firstKey, 'hls_resources'))

        formats = []
        for format_id, video_uri in resources.items():
            if not video_uri:
                continue
            height = self._search_regex(
                r'fl_cdn_(\d+)', format_id, 'height', default=None)
            if not height:
                continue
            format = self._extract_m3u8_formats('https://video.beeg.com/' + video_uri, video_id, ext='mp4', m3u8_id='hls')
            format[0].update({
                'height': int(height),
            })
            formats.extend(format)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': traverse_obj(video, ('fc_facts', firstKey, 'id')),
            'title': traverse_obj(video, ('file', 'stuff', 'sf_name')),
            'description': traverse_obj(video, ('file', 'stuff', 'sf_story')),
            'timestamp': unified_timestamp(traverse_obj(video, ('fc_facts', firstKey, 'fc_created'))),
            'duration': int_or_none(traverse_obj(video, ('file', 'fl_duration'))),
            'tags': traverse_obj(video, ('tags', ..., 'tg_name')),
            'formats': formats,
            'age_limit': self._rta_search(webpage),
        }
