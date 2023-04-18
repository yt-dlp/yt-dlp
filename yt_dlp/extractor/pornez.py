from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    get_element_by_class,
    urljoin,
)


class PornezIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornez\.net/(?:video(?P<id>\w+)|watch)/'
    _TESTS = [{
        'url': 'https://pornez.net/video344819/mistresst-funny_penis_names-wmv/',
        'info_dict': {
            'id': '344819',
            'ext': 'mp4',
            'title': 'mistresst funny_penis_names wmv',
            'thumbnail': r're:^https?://.*\.jpg$',
            'age_limit': 18,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://pornez.net/watch/leana+lovings+stiff+for+stepdaughter/',
        'info_dict': {
            'id': '156161',
            'ext': 'mp4',
            'title': 'Watch leana lovings stiff for stepdaughter porn video.',
            'age_limit': 18,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://pornez.net/videovzs27fj/tutor4k-e14-blue-wave-1080p-nbq-tutor4k-e14-blue-wave/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        if not video_id:
            video_id = self._search_regex(
                r'<link[^>]+\bhref=["\']https?://pornez.net/\?p=(\w+)["\']', webpage, 'id')

        iframe_src = self._html_search_regex(r'<iframe[^>]+src="([^"]+)"', webpage, 'iframe')
        iframe = self._download_webpage(urljoin('https://pornez.net', iframe_src), video_id)

        entries = self._parse_html5_media_entries(iframe_src, iframe, video_id)[0]
        for fmt in entries['formats']:
            height = self._search_regex(r'_(\d+)\.m3u8', fmt['url'], 'height')
            fmt['format_id'] = '%sp' % height
            fmt['height'] = int_or_none(height)

        entries.update({
            'id': video_id,
            'title': (clean_html(get_element_by_class('video-title', webpage))
                      or self._html_search_meta(
                      ['twitter:title', 'og:title', 'description'], webpage, 'title', default=None)),
            'thumbnail': self._html_search_meta(['thumbnailUrl'], webpage, 'thumb', default=None),
            'age_limit': 18,
        })
        return entries
