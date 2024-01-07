from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    clean_html,
    unescapeHTML
)


class CapitalTVCyIE(InfoExtractor):
    _VALID_URL = r'https?://capitaltv\.cy/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://capitaltv.cy/2023/11/07/capital-sports-07-11-2023',
        'info_dict': {
            'id': 'capital-sports-07-11-2023',
            'ext': 'mkv',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data_settings_regex = r'<div[^>]+class="[^"]*elementor-widget-video[^"]*"[^>]*data-settings="([^"]*)"'
        data_settings = self._search_regex(data_settings_regex, webpage, 'data settings', fatal=False)

        if not data_settings:
            raise ExtractorError('Could not find data-settings attribute with video information')

        data_settings_json = unescapeHTML(clean_html(data_settings))
        data = self._parse_json(data_settings_json, video_id, fatal=False)

        youtube_url = traverse_obj(data, ('youtube_url',))

        if not youtube_url:
            raise ExtractorError('Could not find YouTube URL in data-settings')
        print("Webpage content:", video_id)

        return {
            'id': video_id,
            'title': video_id,
            '_type': 'url_transparent',
            'url': youtube_url,
            'ie_key': 'Youtube',
        }
