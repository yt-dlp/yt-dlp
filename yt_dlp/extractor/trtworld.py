from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    traverse_obj,
)


class TrtWorldIE(InfoExtractor):
    _VALID_URL = r'https?://www\.trtworld\.com/video/[\w-]+/[\w-]+-(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.trtworld.com/video/news/turkiye-switches-to-sustainable-tourism-16067690',
        'info_dict': {
            'id': '16067690',
            'ext': 'mp4',
            'title': 'Türkiye switches to sustainable tourism',
            'release_timestamp': 1701529569,
            'release_date': '20231202'
        }
    }, {
        'url': 'https://www.trtworld.com/video/one-offs/frames-from-anatolia-recreating-a-james-bond-scene-in-istanbuls-grand-bazaar-14541780',
        'info_dict': {
            'id': '14541780',
            'ext': 'mp4',
            'title': 'Frames From Anatolia: Bond in the Bazaar',
            'release_timestamp': 1692440844,
            'release_date': '20230819'
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        nuxtjs_data = self._search_nuxt_data(webpage, display_id)
        video_url = traverse_obj(nuxtjs_data, ('videoData', 'content', 'platforms', 'website', 'metadata', 'hls_url', ))
        published_date_str = traverse_obj(nuxtjs_data, ('videoData', 'content', 'published', 'date', ))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, display_id)
        return {
            'id': str(display_id),
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': parse_iso8601(published_date_str),
            'title': self._html_extract_title(webpage)
        }
