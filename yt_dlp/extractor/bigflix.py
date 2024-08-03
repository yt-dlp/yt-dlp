import base64
import re
import urllib.parse

from .common import InfoExtractor


class BigflixIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bigflix\.com/.+/(?P<id>[0-9]+)'
    _TESTS = [{
        # 2 formats
        'url': 'http://www.bigflix.com/Tamil-movies/Drama-movies/Madarasapatinam/16070',
        'info_dict': {
            'id': '16070',
            'ext': 'mp4',
            'title': 'Madarasapatinam',
            'description': 'md5:9f0470b26a4ba8e824c823b5d95c2f6b',
            'formats': 'mincount:2',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # multiple formats
        'url': 'http://www.bigflix.com/Malayalam-movies/Drama-movies/Indian-Rupee/15967',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<div[^>]+class=["\']pagetitle["\'][^>]*>(.+?)</div>',
            webpage, 'title')

        def decode_url(quoted_b64_url):
            return base64.b64decode(urllib.parse.unquote(
                quoted_b64_url)).decode('utf-8')

        formats = []
        for height, encoded_url in re.findall(
                r'ContentURL_(\d{3,4})[pP][^=]+=([^&]+)', webpage):
            video_url = decode_url(encoded_url)
            f = {
                'url': video_url,
                'format_id': f'{height}p',
                'height': int(height),
            }
            if video_url.startswith('rtmp'):
                f['ext'] = 'flv'
            formats.append(f)

        file_url = self._search_regex(
            r'file=([^&]+)', webpage, 'video url', default=None)
        if file_url:
            video_url = decode_url(file_url)
            if all(f['url'] != video_url for f in formats):
                formats.append({
                    'url': decode_url(file_url),
                })

        description = self._html_search_meta('description', webpage)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
        }
