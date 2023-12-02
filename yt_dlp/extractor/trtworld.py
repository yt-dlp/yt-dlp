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
        nuxtjs_data = self._search_nuxt_data(webpage, display_id)['videoData']['content']
        formats = []
        for media_url in traverse_obj(nuxtjs_data, (
                'platforms', ('website', 'ott'), 'metadata', ('hls_url', 'url'), {url_or_none})):
            # Website sometimes serves mp4 files under `hls_url` key
            if media_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(media_url, display_id, fatal=False))
            else:
                formats.append({
                    'format_id': 'http',
                    'url': media_url,
                })
        if not formats:
            if youtube_id := traverse_obj(nuxtjs_data, ('platforms', 'youtube', 'metadata', 'youtubeId')):
                return self.url_result(youtube_id, 'Youtube')
            raise ExtractorError('No video found', expected=True)

        return {
            'id': display_id,
            'formats': formats,
            **traverse_obj(nuxtjs_data, ('platforms', ('website', 'ott'), {
                'title': ('fields', 'title', 'text'),
                'description': ('fields', 'description', 'text'),
                'thumbnail': ('fields', 'thumbnail', 'url', {url_or_none}),
                'release_timestamp': ('published', 'date', {parse_iso8601}),
            }), get_all=False),
        }
