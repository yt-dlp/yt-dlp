from .common import InfoExtractor
from ..utils import clean_html, get_element_by_class


class TelegramEmbedIE(InfoExtractor):
    IE_NAME = 'telegram:embed'
    _VALID_URL = r'https?://t\.me/(?P<channel_name>[^/]+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://t.me/europa_press/613',
        'info_dict': {
            'id': '613',
            'ext': 'mp4',
            'title': 'Europa Press',
            'description': '6ce2d7e8d56eda16d80607b23db7b252',
            'thumbnail': r're:^https?:\/\/cdn.*?telesco\.pe\/file\/\w+',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, query={'embed': 0})
        webpage_embed = self._download_webpage(url, video_id, query={'embed': 1}, note='Downloading ermbed page')

        formats = [{
            'url': self._proto_relative_url(self._search_regex(
                '<video[^>]+src="([^"]+)"', webpage_embed, 'source')),
            'ext': 'mp4',
        }]
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage, default=None),
            'description': self._html_search_meta(
                ['og:description', 'twitter:description'], webpage,
                default=clean_html(get_element_by_class('tgme_widget_message_text', webpage_embed))),
            'thumbnail': self._search_regex(
                r'tgme_widget_message_video_thumb"[^>]+background-image:url\(\'([^\']+)\'\)',
                webpage_embed, 'thumbnail'),
            'formats': formats,
        }
