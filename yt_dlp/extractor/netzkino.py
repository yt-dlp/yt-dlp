from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    js_to_json,
    parse_iso8601,
)


class NetzkinoIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?netzkino\.de/\#!/[^/]+/(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'https://www.netzkino.de/#!/scifikino/rakete-zum-mond',
        'md5': '92a3f8b76f8d7220acce5377ea5d4873',
        'info_dict': {
            'id': 'rakete-zum-mond',
            'ext': 'mp4',
            'title': 'Rakete zum Mond \u2013 Jules Verne',
            'description': 'md5:f0a8024479618ddbfa450ff48ffa6c60',
            'upload_date': '20120813',
            'thumbnail': r're:https?://.*\.jpg$',
            'timestamp': 1344858571,
            'age_limit': 12,
        },
        'params': {
            'skip_download': 'Download only works from Germany',
        }
    }, {
        'url': 'https://www.netzkino.de/#!/filme/dr-jekyll-mrs-hyde-2',
        'md5': 'c7728b2dadd04ff6727814847a51ef03',
        'info_dict': {
            'id': 'dr-jekyll-mrs-hyde-2',
            'ext': 'mp4',
            'title': 'Dr. Jekyll & Mrs. Hyde 2',
            'description': 'md5:c2e9626ebd02de0a794b95407045d186',
            'upload_date': '20190130',
            'thumbnail': r're:https?://.*\.jpg$',
            'timestamp': 1548849437,
            'age_limit': 18,
        },
        'params': {
            'skip_download': 'Download only works from Germany',
        }
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        api_url = 'https://api.netzkino.de.simplecache.net/capi-2.0a/movies/%s.json?d=www' % video_id
        info = self._download_json(api_url, video_id)
        custom_fields = info['custom_fields']

        production_js = self._download_webpage(
            'http://www.netzkino.de/beta/dist/production.min.js', video_id,
            note='Downloading player code')
        avo_js = self._search_regex(
            r'var urlTemplate=(\{.*?"\})',
            production_js, 'URL templates')
        templates = self._parse_json(
            avo_js, video_id, transform_source=js_to_json)

        suffix = {
            'hds': '.mp4/manifest.f4m',
            'hls': '.mp4/master.m3u8',
            'pmd': '.mp4',
        }
        film_fn = custom_fields['Streaming'][0]
        formats = [{
            'format_id': key,
            'ext': 'mp4',
            'url': tpl.replace('{}', film_fn) + suffix[key],
        } for key, tpl in templates.items()]

        return {
            'id': video_id,
            'formats': formats,
            'title': info['title'],
            'age_limit': int_or_none(custom_fields.get('FSK')[0]),
            'timestamp': parse_iso8601(info.get('date'), delimiter=' '),
            'description': clean_html(info.get('content')),
            'thumbnail': info.get('thumbnail'),
        }
