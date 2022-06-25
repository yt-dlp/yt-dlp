from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj


class PremiershipRugbyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)premiershiprugby\.(?:com)/watch/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.premiershiprugby.com/watch/full-match-harlequins-v-newcastle-falcons',
        'info_dict': {
            'id': '0_mbkb7ldt',
            'title': 'Full Match: Harlequins v Newcastle Falcons',
            'ext': 'mp4',
            'thumbnail': 'https://open.http.mp.streamamg.com/p/3000914/sp/300091400/thumbnail/entry_id/0_mbkb7ldt//width/960/height/540/type/1/quality/75',
            'duration': 6093.0,
            'tags': ['video'],
            'categories': ['Full Match', 'Harlequins', 'Newcastle Falcons', 'gallaher premiership'],
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        json_data = self._download_json(
            f'https://article-cms-api.incrowdsports.com/v2/articles/slug/{display_id}',
            display_id, query={'clientId': 'PRL'})['data']['article']

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            json_data['heroMedia']['content']['videoLink'], display_id)

        return {
            'id': json_data['heroMedia']['content']['sourceSystemId'],
            'display_id': display_id,
            'title': traverse_obj(json_data, ('heroMedia', 'title')),
            'formats': formats,
            'subtitles': subs,
            'thumbnail': traverse_obj(json_data, ('heroMedia', 'content', 'videoThumbnail')),
            'duration': int_or_none(traverse_obj(json_data, ('heroMedia', 'content', 'metadata', 'msDuration')), scale=1000),
            'tags': json_data.get('tags'),
            'categories': traverse_obj(json_data, ('categories', ..., 'text')),
        }
