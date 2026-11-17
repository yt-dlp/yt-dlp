from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
    traverse_obj,
    try_get,
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
            'upload_date': '20220131',
            'timestamp': 1643656455,
            'display_id': '2540839',
        },
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
            'display_id': '2569965',
            'upload_date': '20220131',
        },
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
            f'https://store.externulls.com/facts/file/{video_id}',
            video_id, f'Downloading JSON for {video_id}')

        fc_facts = video.get('fc_facts')
        first_fact = {}
        for fact in fc_facts:
            if not first_fact or try_get(fact, lambda x: x['id'] < first_fact['id']):
                first_fact = fact

        resources = traverse_obj(video, ('file', 'hls_resources')) or first_fact.get('hls_resources')

        formats = []
        for format_id, video_uri in resources.items():
            if not video_uri:
                continue
            height = int_or_none(self._search_regex(r'fl_cdn_(\d+)', format_id, 'height', default=None))
            current_formats = self._extract_m3u8_formats(f'https://video.beeg.com/{video_uri}', video_id, ext='mp4', m3u8_id=str(height))
            for f in current_formats:
                f['height'] = height
            formats.extend(current_formats)

        return {
            'id': video_id,
            'display_id': str_or_none(first_fact.get('id')),
            'title': traverse_obj(video, ('file', 'stuff', 'sf_name')),
            'description': traverse_obj(video, ('file', 'stuff', 'sf_story')),
            'timestamp': unified_timestamp(first_fact.get('fc_created')),
            'duration': int_or_none(traverse_obj(video, ('file', 'fl_duration'))),
            'tags': traverse_obj(video, ('tags', ..., 'tg_name')),
            'formats': formats,
            'age_limit': self._rta_search(webpage),
        }
