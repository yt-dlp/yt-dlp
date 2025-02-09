from .common import InfoExtractor
from ..utils import (
    try_get,
    unified_timestamp,
)


class CGTNIE(InfoExtractor):
    _VALID_URL = r'https?://news\.cgtn\.com/news/[0-9]{4}-[0-9]{2}-[0-9]{2}/[a-zA-Z0-9-]+-(?P<id>[a-zA-Z0-9-]+)/index\.html'
    _TESTS = [
        {
            'url': 'https://news.cgtn.com/news/2021-03-09/Up-and-Out-of-Poverty-Ep-1-A-solemn-promise-YuOUaOzGQU/index.html',
            'info_dict': {
                'id': 'YuOUaOzGQU',
                'ext': 'mp4',
                'title': 'Up and Out of Poverty Ep. 1: A solemn promise',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1615295940,
                'upload_date': '20210309',
                'categories': ['Video'],
            },
            'params': {
                'skip_download': True,
            },
        }, {
            'url': 'https://news.cgtn.com/news/2021-06-06/China-Indonesia-vow-to-further-deepen-maritime-cooperation-10REvJCewCY/index.html',
            'info_dict': {
                'id': '10REvJCewCY',
                'ext': 'mp4',
                'title': 'China, Indonesia vow to further deepen maritime cooperation',
                'thumbnail': r're:^https?://.*\.png$',
                'description': 'China and Indonesia vowed to upgrade their cooperation into the maritime sector and also for political security, economy, and cultural and people-to-people exchanges.',
                'creators': ['CGTN'],
                'categories': ['China'],
                'timestamp': 1622950200,
                'upload_date': '20210606',
            },
            'params': {
                'skip_download': False,
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        download_url = self._html_search_regex(r'data-video ="(?P<url>.+m3u8)"', webpage, 'download_url')
        datetime_str = self._html_search_regex(
            r'<span class="date">\s*(.+?)\s*</span>', webpage, 'datetime_str', fatal=False)
        category = self._html_search_regex(
            r'<span class="section">\s*(.+?)\s*</span>', webpage, 'category', fatal=False)
        author = self._search_regex(
            r'<div class="news-author-name">\s*(.+?)\s*</div>', webpage, 'author', default=None)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': self._extract_m3u8_formats(download_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls'),
            'categories': [category] if category else None,
            'creators': [author] if author else None,
            'timestamp': try_get(unified_timestamp(datetime_str), lambda x: x - 8 * 3600),
        }
