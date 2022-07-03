from .common import InfoExtractor
from ..utils import try_get, unified_strdate


class StardeosIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?stardeos\.com/video/(?P<id>[a-z0-9]+)'

    _TESTS = [{
        'url': 'https://stardeos.com/video/614fb673fc6c574634680d41',
        'info_dict': {
            'id': '614fb673fc6c574634680d41',
            'ext': 'mp4',
            'title': 'Stardeos, la alternativa más justa a YouTube',
            'thumbnail': 'https://thumbnails.stardeos.com/557a86d9-e1c6-4515-bc54-50418f99699a.jpg',
            'uploader': 'Stardeos',
            'tags': ['stardeos', 'trailer', 'youtube', 'comienzo', 'alternativa', 'aggregations', 'stardeos.com'],
            'upload_date': '20210715',
            'description': '',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'This video requires cookies'
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        if not self._cookies_passed:
            raise self.raise_login_required('This video requires cookies', method='cookies')

        webpage = self._download_webpage(url, id, headers={'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36'})

        data_json = self._search_nextjs_data(webpage, id)['props']['pageProps']['video']

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(data_json['video'], id)
        self._sort_formats(formats)

        return {
            'id': id,
            'title': data_json.get('title'),
            'description': data_json.get('description'),
            'tags': data_json.get('tags'),
            'uploader': try_get(data_json, lambda x: x['creator']['username']),
            'upload_date': unified_strdate(data_json.get('createdAt')),
            'thumbnail': data_json.get('thumbnail'),
            'formats': formats,
            'subtitles': subtitles
        }
