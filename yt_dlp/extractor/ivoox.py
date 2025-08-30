from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, url_or_none, urljoin
from ..utils.traversal import traverse_obj


class IvooxIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?ivoox\.com/(?:\w{2}/)?[^/?#]+_rf_(?P<id>[0-9]+)_1\.html',
        r'https?://go\.ivoox\.com/rf/(?P<id>[0-9]+)',
    )
    _TESTS = [{
        'url': 'https://www.ivoox.com/dex-08x30-rostros-del-mal-los-asesinos-en-audios-mp3_rf_143594959_1.html',
        'md5': '993f712de5b7d552459fc66aa3726885',
        'info_dict': {
            'id': '143594959',
            'ext': 'mp3',
            'timestamp': 1742731200,
            'channel': 'DIAS EXTRAÑOS con Santiago Camacho',
            'title': 'DEx 08x30 Rostros del mal: Los asesinos en serie que aterrorizaron España',
            'description': 'md5:eae8b4b9740d0216d3871390b056bb08',
            'uploader': 'Santiago Camacho',
            'thumbnail': 'https://static-1.ivoox.com/audios/c/d/5/2/cd52f46783fe735000c33a803dce2554_XXL.jpg',
            'upload_date': '20250323',
            'episode': 'DEx 08x30 Rostros del mal: Los asesinos en serie que aterrorizaron España',
            'duration': 11837,
            'tags': ['españa', 'asesinos en serie', 'arropiero', 'historia criminal', 'mataviejas'],
        },
    }, {
        'url': 'https://go.ivoox.com/rf/143594959',
        'only_matching': True,
    }, {
        'url': 'https://www.ivoox.com/en/campodelgas-28-03-2025-audios-mp3_rf_144036942_1.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id, fatal=False)

        data = self._search_nuxt_data(
            webpage, media_id, fatal=False, traverse=('data', 0, 'data', 'audio'))

        direct_download = self._download_json(
            f'https://vcore-web.ivoox.com/v1/public/audios/{media_id}/download-url', media_id, fatal=False,
            note='Fetching direct download link', headers={'Referer': url})

        download_paths = {
            *traverse_obj(direct_download, ('data', 'downloadUrl', {str}, filter, all)),
            *traverse_obj(data, (('downloadUrl', 'mediaUrl'), {str}, filter)),
        }

        formats = []
        for path in download_paths:
            formats.append({
                'url': urljoin('https://ivoox.com', path),
                'http_headers': {'Referer': url},
            })

        return {
            'id': media_id,
            'formats': formats,
            'uploader': self._html_search_regex(r'data-prm-author="([^"]+)"', webpage, 'author', default=None),
            'timestamp': parse_iso8601(
                self._html_search_regex(r'data-prm-pubdate="([^"]+)"', webpage, 'timestamp', default=None)),
            'channel': self._html_search_regex(r'data-prm-podname="([^"]+)"', webpage, 'channel', default=None),
            'title': self._html_search_regex(r'data-prm-title="([^"]+)"', webpage, 'title', default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
            **self._search_json_ld(webpage, media_id, default={}),
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('image', {url_or_none}),
                'timestamp': ('uploadDate', {parse_iso8601(delimiter=' ')}),
                'duration': ('duration', {int_or_none}),
                'tags': ('tags', ..., 'name', {str}),
            }),
        }
