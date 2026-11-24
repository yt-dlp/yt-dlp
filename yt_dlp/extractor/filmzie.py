from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class FilmzieIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?filmzie\.com/content/(?P<id>[a-zA-Z0-9-]+)'
    _TESTS = [{
        'url': 'https://filmzie.com/content/intermate-2019',
        'info_dict': {
            'id': '63a43a6c9b52a1714855eba0',
            'ext': 'mp4',
            'description': 'md5:4dc313028ad2850aaea4084e1814da9e',
            'title': 'Intermate',
        },
    }, {
        'url': 'https://filmzie.com/content/southern-star-2013',
        'info_dict': {
            'id': '62d10d24d68da3293a90bbc5',
            'ext': 'mp4',
            'description': 'md5:259be286dd434bc416841d6cc6abe30b',
            'title': 'Southern Star',
        },
    }]

    def _real_extract(self, url):
        content_id = self._match_id(url)
        webpage = self._download_webpage(url, content_id)

        c_data = self._search_regex(r'window\[\'APP_STATE\'\]\s*=\s*(\{.*?\});', webpage, 'c_data')
        c_data_content = self._parse_json(c_data, content_id)['contentPage']['content']

        video_id = c_data_content['videos'][0]['id']
        video_data = self._download_json(f'https://filmzie.com/api/v1/video/stream/{video_id}', content_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_data['data']['source']['hlsV2'], video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(c_data_content, {
                'description': ('description', {str}),
                'title': ('title', {str}),
            }),
        }
