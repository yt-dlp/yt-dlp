from .common import InfoExtractor


class RedzidzirdilatvijuIE(InfoExtractor):
    _VALID_URL = r'https?://redzidzirdilatviju\.lv/(?:en|lv)/search/movie/(?P<id>\d+)'
    IE_DESC = 'Redzidzirdilatviju'
    _TESTS = [{
        'url': 'https://redzidzirdilatviju.lv/en/search/movie/175277',
        'info_dict': {
            'id': '175277',
            'ext': 'mp4',
            'title': 'Krievijas imperatora Nikolaja II vizīte Rīgā',
        },
        'skip': 'Test video may not be available',
    }, {
        'url': 'https://redzidzirdilatviju.lv/lv/search/movie/175277',
        'only_matching': True,
    }, {
        'url': 'https://redzidzirdilatviju.lv/en/search/movie/160825',
        'info_dict': {
            'id': '160825',
            'ext': 'mp4',
            'title': 'Mītavas zemkopības skolas audzēkņi pastaigā un vingrošanas svētkos',
        },
        'skip': 'Test video may not be available',
    }, {
        'url': 'https://redzidzirdilatviju.lv/lv/search/movie/160825',
        'only_matching': True,
    }, {
        'url': 'https://redzidzirdilatviju.lv/en/search/movie/161042',
        'info_dict': {
            'id': '161042',
            'ext': 'mp4',
            'title': 'Kinomaterialāli Nr. 5',
        },
        'skip': 'Test video may not be available',
    }, {
        'url': 'https://redzidzirdilatviju.lv/lv/search/movie/161042',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        doc = self._download_json(
            'https://www.redzidzirdilatviju.lv/index', video_id,
            query={
                'wt': 'json',
                'q': f'ss_item_type:(movie OR photo OR sound) AND ss_item_entity_id:{video_id}',
                'rows': '1'
            })['response']['docs'][0]
        video_filename = doc['ss_movie$field_video$file$name']

        if not video_filename.endswith('.mp4'):
            video_filename += '.mp4'

        return {
            'id': video_id,
            'title': doc.get('ts_movie$field_title') or doc.get('tm_movie$field_title'),
            'formats': self._extract_m3u8_formats(
                f'https://filmas.arhivi.lv:30443/s/{video_filename}/playlist.m3u8', video_id, 'mp4'),
        }
