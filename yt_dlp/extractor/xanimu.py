import re

from ..utils import int_or_none
from .common import InfoExtractor


class XanimuIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?xanimu\.com/(?:(?P<id>\d+)-)?(?P<display_id>[^/]+)/?'
    _TESTS = [{
        'url': 'https://xanimu.com/51944-the-princess-the-frog-hentai/',
        'md5': '899b88091d753d92dad4cb63bbf357a7',
        'info_dict': {
            'id': '51944',
            'display_id': 'the-princess-the-frog-hentai',
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
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('display_id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, video_id)

        title = self._search_regex(r'[\'"]headline[\'"]:\s*[\'"]([^"]+)[\'"]',
                                   webpage, 'title', default=None)
        if not title:
            title = self._html_extract_title(webpage)

        thumbnail = self._html_search_meta('thumbnailUrl', webpage, default=None)

        duration = int_or_none(self._search_regex(r'duration:\s*[\'"]([^\'"]+?)[\'"]',
                               webpage, 'duration', fatal=False))

        formats = []
        for format in ["videoHigh", "videoLow"]:
            format_url = self._search_regex(r'var\s+%s\s*=\s*[\'"]([^\'"]+)[\'"]'
                                            % re.escape(format), webpage, format, default=None)
            if format_url:
                formats.append({
                    'url': format_url.replace(r'\/', '/'),
                    'format_id': format,
                    'quality': -2 if format.endswith('Low') else None,
                })

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'title': title,
            'thumbnail': thumbnail,
            'description': self._html_search_meta('description', webpage, default=None),
            'duration': duration,
            'age_limit': 18
        }
