from .common import InfoExtractor


class SasflixIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?sasflix\.ru/topics/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://sasflix.ru/topics/a7851209-c06a-446a-9adc-aaf92ef8fae0',
        'md5': 'f63c16f8b48325731ca3529d0cad776c',
        'info_dict': {
            'id': 'a7851209-c06a-446a-9adc-aaf92ef8fae0',
            'title': 'Сильный паспорт // Долину обездолили // Венесуэле хана №177 / Публикации / Сасфликс',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        topic_id = self._match_id(url)
        webpage = self._download_webpage(url, topic_id)
        video_id = self._search_regex(r'id="video-player-([\w-]+)"',
                                      webpage, 'video id')

        return {
            'id': topic_id,
            'formats': self._extract_m3u8_formats(
                f'https://sasflix.ru/api/video/{video_id}', video_id),
            'title': self._og_search_title(webpage),
        }
