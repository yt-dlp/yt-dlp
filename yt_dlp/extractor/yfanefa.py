import re

from .common import InfoExtractor
from ..utils import ExtractorError


class YfanefaIE(InfoExtractor):
    IE_NAME = 'yfanefa'

    _VALID_URL = r'https?://(?:www\.)?yfanefa\.com/(?P<id>[^?#]+)'

    _TESTS = [{
        'url': 'https://www.yfanefa.com/record/2717',
        'info_dict': {
            'id': 'record/2717',
            'ext': 'mp4',
            'title': 'THE HALLAMSHIRE RIFLES LEAVING SHEFFIELD, 1914',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.yfanefa.com/news/53',
        'info_dict': {
            'id': 'news/53',
            'ext': 'mp4',
            'title': 'Memory Bank:  Bradford Launch',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.yfanefa.com/evaluating_nature_matters',
        'info_dict': {
            'id': 'evaluating_nature_matters',
            'ext': 'mp4',
            'title': 'Evaluating Nature Matters',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage) or self._html_extract_title(webpage)

        player_match = re.search(r'iwPlayer\.options\[[^\]]+\]\s*=\s*({.*?});', webpage, re.DOTALL)
        if not player_match:
            raise ExtractorError('Could not find player configuration')

        config_str = player_match.group(1).replace('\\/', '/')
        url_match = re.search(r'"url":"(https://media\.yfanefa\.com/storage/v1/(?:hls|file)/[^"]+)"', config_str)
        sig_match = re.search(r'"signature":"(\?[^"]*)"', config_str)

        if not url_match:
            raise ExtractorError('Could not extract video URL')

        m3u8_url = url_match.group(1)

        if sig_match and sig_match.group(1):
            signature = sig_match.group(1)
            if signature and not signature.startswith('?'):
                signature = '?' + signature
            m3u8_url += signature

        m3u8_url = m3u8_url.replace('\\', '')

        if m3u8_url.endswith('.m3u8'):
            formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')
        else:
            formats = [{
                'url': m3u8_url,
                'ext': 'mp4',
            }]

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'http_headers': {'Referer': url},
        }
