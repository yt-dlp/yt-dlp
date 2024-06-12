from .common import InfoExtractor
from ..utils import traverse_obj


class CellebriteIE(InfoExtractor):
    _VALID_URL = r'https?://cellebrite\.com/(?:\w+)?/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://cellebrite.com/en/collect-data-from-android-devices-with-cellebrite-ufed/',
        'info_dict': {
            'id': '16025876',
            'ext': 'mp4',
            'description': 'md5:174571cb97083fd1d457d75c684f4e2b',
            'thumbnail': 'https://cellebrite.com/wp-content/uploads/2021/05/Chat-Capture-1024x559.png',
            'title': 'Ask the Expert: Chat Capture - Collect Data from Android Devices in Cellebrite UFED',
            'duration': 455,
            'tags': [],
        },
    }, {
        'url': 'https://cellebrite.com/en/how-to-lawfully-collect-the-maximum-amount-of-data-from-android-devices/',
        'info_dict': {
            'id': '29018255',
            'ext': 'mp4',
            'duration': 134,
            'tags': [],
            'description': 'md5:e9a3d124c7287b0b07bad2547061cacf',
            'thumbnail': 'https://cellebrite.com/wp-content/uploads/2022/07/How-to-Lawfully-Collect-the-Maximum-Amount-of-Data-From-Android-Devices.png',
            'title': 'Android Extractions Explained',
        },
    }]

    def _get_formats_and_subtitles(self, json_data, display_id):
        formats = [{'url': url} for url in traverse_obj(json_data, ('mp4', ..., 'url')) or []]
        subtitles = {}

        for url in traverse_obj(json_data, ('hls', ..., 'url')) or []:
            fmt, sub = self._extract_m3u8_formats_and_subtitles(
                url, display_id, ext='mp4', headers={'Referer': 'https://play.vidyard.com/'})
            formats.extend(fmt)
            self._merge_subtitles(sub, target=subtitles)

        return formats, subtitles

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        player_uuid = self._search_regex(
            r'<img\s[^>]*\bdata-uuid\s*=\s*"([^"\?]+)', webpage, 'player UUID')
        json_data = self._download_json(
            f'https://play.vidyard.com/player/{player_uuid}.json', display_id)['payload']['chapters'][0]

        formats, subtitles = self._get_formats_and_subtitles(json_data['sources'], display_id)
        return {
            'id': str(json_data['videoId']),
            'title': json_data.get('name') or self._og_search_title(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'description': json_data.get('description') or self._og_search_description(webpage),
            'duration': json_data.get('seconds'),
            'tags': json_data.get('tags'),
            'thumbnail': self._og_search_thumbnail(webpage),
            'http_headers': {'Referer': 'https://play.vidyard.com/'},
        }
