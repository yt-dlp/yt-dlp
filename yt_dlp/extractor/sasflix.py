from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class SasflixIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?sasflix\.ru/topics/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://sasflix.ru/topics/a7851209-c06a-446a-9adc-aaf92ef8fae0',
        'md5': 'f63c16f8b48325731ca3529d0cad776c',
        'info_dict': {
            'id': 'a7851209-c06a-446a-9adc-aaf92ef8fae0',
            'title': 'Сильный паспорт // Долину обездолили // Венесуэле хана №177',
            'duration': 2024,
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        topic_id = self._match_id(url)
        topic_data = self._download_json(
            f'https://sasflix.ru/api/web/topics/{topic_id}', topic_id)

        if not topic_data.get('has_video'):
            raise ExtractorError("no video available")

        video_id = traverse_obj(topic_data, ('video', 'id'))

        return {
            'id': topic_id,
            'formats': self._extract_m3u8_formats(
                f'https://sasflix.ru/api/video/{video_id}', video_id),
            'title': topic_data.get('title'),
            'duration': traverse_obj(topic_data, ('video', 'duration'))
        }
