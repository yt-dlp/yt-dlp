import re

from .common import InfoExtractor
from ..utils import int_or_none


class XanimuIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?xanimu\.com/(?P<id>[^/]+)/?'
    _TESTS = [{
        'url': 'https://xanimu.com/51944-the-princess-the-frog-hentai/',
        'md5': '899b88091d753d92dad4cb63bbf357a7',
        'info_dict': {
            'id': '51944-the-princess-the-frog-hentai',
            'ext': 'mp4',
            'title': 'The Princess + The Frog Hentai',
            'thumbnail': 'https://xanimu.com/storage/2020/09/the-princess-and-the-frog-hentai.jpg',
            'description': r're:^Enjoy The Princess \+ The Frog Hentai',
            'duration': 207.0,
            'age_limit': 18
        }
    }, {
        'url': 'https://xanimu.com/huge-expansion/',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []
        for format in ['videoHigh', 'videoLow']:
            format_url = self._search_json(r'var\s+%s\s*=' % re.escape(format), webpage, format,
                                           video_id, default=None, contains_pattern=r'[\'"]([^\'"]+)[\'"]')
            if format_url:
                formats.append({
                    'url': format_url,
                    'format_id': format,
                    'quality': -2 if format.endswith('Low') else None,
                })

        return {
            'id': video_id,
            'formats': formats,
            'title': self._search_regex(r'[\'"]headline[\'"]:\s*[\'"]([^"]+)[\'"]', webpage,
                                        'title', default=None) or self._html_extract_title(webpage),
            'thumbnail': self._html_search_meta('thumbnailUrl', webpage, default=None),
            'description': self._html_search_meta('description', webpage, default=None),
            'duration': int_or_none(self._search_regex(r'duration:\s*[\'"]([^\'"]+?)[\'"]',
                                    webpage, 'duration', fatal=False)),
            'age_limit': 18
        }
