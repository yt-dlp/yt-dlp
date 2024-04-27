from .common import InfoExtractor


class MoverIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mover\.uz/watch/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://mover.uz/watch/cMSqJpZm',
        'md5': 'a0b50df896154eda275a37219c214fd4',
        'info_dict': {
            'id': 'cMSqJpZm',
            'ext': 'mp4',
            'title': '16.38 A Fool Moon Night 98.51% 4824x combo – osu! mania',
            'thumbnail': 'https://i.mover.uz/cMSqJpZm_h2.jpg',
        }
    }, {
        'url': 'https://mover.uz/watch/kLB0KQKe',
        'md5': '3c7dc53488675ef003db803c2d0f124e',
        'info_dict': {
            'id': 'kLB0KQKe',
            'ext': 'mp4',
            'title': 'DEADPOOL & WOLVERINE Trailer (2024) Extended | 4K UHD',
            'thumbnail': 'https://i.mover.uz/kLB0KQKe_h2.jpg',
        }
    }, {
        'url': 'https://mover.uz/watch/yYfmpNRa',
        'md5': 'a142825db45c9ef8f495635b6f227f3a',
        'info_dict': {
            'id': 'yYfmpNRa',
            'ext': 'mp4',
            'title': 'Новое поколение Mazda 6. Дождались',
            'thumbnail': 'https://i.mover.uz/yYfmpNRa_h2.jpg',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_meta(['og:title'], webpage, default=None)
        thumbnail = self._html_search_meta(['og:image'], webpage, default=None)
        mp4_url = 'https://v.mover.uz/' + video_id + "_h.mp4"

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'url': mp4_url,
        }
