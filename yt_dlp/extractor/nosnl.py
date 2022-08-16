from .common import InfoExtractor
from ..utils import traverse_obj


class NOSNLIE(InfoExtractor):
    _VALID_URL = r'https?://nos\.nl/\w+/\w+/(?P<display_id>[\w-]+)'
    _TESTS = [
        {
            'url': 'https://nos.nl/nieuwsuur/artikel/2440353-verzakking-door-droogte-dreigt-tot-een-miljoen-kwetsbare-huizen',
            'info_dict': {
                'id': 'fixme',
                'ext': 'mp4',
            }
        }
    ]

    def _get_video_generator(self, nextjs_json, display_id):
        for item in nextjs_json.get('items'):
            if item.get('type') == 'video':
                formats, subtitle = self._extract_m3u8_formats_and_subtitles(
                    traverse_obj(item, ('source', 'url')), display_id)

                yield {
                    'id': item['id'],
                    'title': item.get('title'),
                    'description': item.get('description'),
                    'formats': formats,
                    'subtitles': subtitle,

                }

    def _real_extract(self, url):
        display_id = self._match_valid_url(url).group('display_id')
        webpage = self._download_webpage(url, display_id)

        nextjs_json = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['data']
        video_generator = self._get_video_generator(nextjs_json, display_id)
        return self.playlist_result(video_generator, nextjs_json['id'], nextjs_json.get('title'))