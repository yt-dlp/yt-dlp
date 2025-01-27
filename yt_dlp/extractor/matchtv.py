from .common import InfoExtractor
from .webcaster import WebcasterBaseIE, WebcasterFeedBaseIE


class MatchTVIE(InfoExtractor):
    _VALID_URL = [
        r'https?://matchtv\.ru/on-air/?(?:$|[?#])',
        r'https?://video\.matchtv\.ru/iframe/channel/106/?(?:$|[?#])',
    ]
    _TESTS = [{
        'url': 'http://matchtv.ru/on-air/',
        'info_dict': {
            'id': 'matchtv-live',
            'ext': 'mp4',
            'title': r're:^Матч ТВ - Прямой эфир \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://video.matchtv.ru/iframe/channel/106',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = 'matchtv-live'
        webpage = self._download_webpage('https://video.matchtv.ru/iframe/channel/106', video_id)
        video_url = self._html_search_regex(
            r'data-config="config=(https?://[^?"]+)[?"]', webpage, 'video URL').replace('/feed/', '/media/') + '.m3u8'
        return {
            'id': video_id,
            'title': 'Матч ТВ - Прямой эфир',
            'is_live': True,
            'formats': self._extract_m3u8_formats(video_url, video_id, 'mp4', live=True),
        }


class MatchTVVideoIE(WebcasterBaseIE):
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://bl\.video\.matchtv\.ru/(?:quote|media)/start/(?:api_)?free_(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://bl.video.matchtv.ru/media/start/free_675ea0e4b4b1d54d21f9b52db6624199/17_635869/dadc378c196047e4d121725bbb6f9717/2208978000',
        'md5': 'ad07e90a3f041d452864116fb60b7f57',
        'info_dict': {
            'id': '675ea0e4b4b1d54d21f9b52db6624199',
            'ext': 'mp4',
            'title': '«Золотой дубль Черчесова». Специальный репортаж',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'https://bl.video.matchtv.ru/quote/start/free_7a87d97313e49cdfa3b960b10da25d0a/q139002/9d09bfff78f766dee404f82c1875be76/4854542998',
        'md5': '52c1bd5c7fc1329834c37f638280f562',
        'info_dict': {
            'id': '7a87d97313e49cdfa3b960b10da25d0a',
            'ext': 'mp4',
            'title': 'Ювентус - Верона. Отмененный гол Кина (видео). Чемпионат Италии. Футбол',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }]


class MatchTVFeedIE(WebcasterFeedBaseIE):
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://bl\.video\.matchtv\.ru/feed/start/(?:api_)?free_(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://bl.video.matchtv.ru/feed/start/free_675ea0e4b4b1d54d21f9b52db6624199/17_635869/dadc378c196047e4d121725bbb6f9717/2208978000',
        'md5': 'ad07e90a3f041d452864116fb60b7f57',
        'info_dict': {
            'id': '675ea0e4b4b1d54d21f9b52db6624199',
            'ext': 'mp4',
            'title': '«Золотой дубль Черчесова». Специальный репортаж',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://matchtv.ru/football/matchtvvideo_NI1593368_clip_Zolotoj_dubl_Cherchesova_Specialnyj_reportazh',
        'md5': 'ad07e90a3f041d452864116fb60b7f57',
        'info_dict': {
            'id': '675ea0e4b4b1d54d21f9b52db6624199',
            'ext': 'mp4',
            'title': '«Золотой дубль Черчесова». Специальный репортаж',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1192.0,
            'age_limit': 0,
            'upload_date': '20220517',
            'description': 'md5:081475ff4baa80570b027e295233bee6',
            'uploader': 'МАТЧ ТВ',
            'timestamp': 1652781632,
        },
    }, {
        'url': 'https://matchtv.ru/football/rossija/kubok_rossii/matchtvvideo_NI2100168_translation_FONBET_Kubok_Rossii_Tekstilshhik___Spartak_Kostroma',
        'md5': '26472920ff298a4516552e755ae45493',
        'info_dict': {
            'id': 'b6570efa80dc28df18523237d3f14a5b',
            'ext': 'mp4',
            'title': 'FONBET Кубок России по футболу сезона 2024 - 2025 гг. Текстильщик - Спартак Кострома',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 7986.0,
            'description': 'md5:1068ce14021b7da6bb36eb6c7e43bdd1',
            'timestamp': 1725379522,
            'upload_date': '20240903',
            'age_limit': 0,
            'uploader': 'МАТЧ ТВ',
        },
    }, {
        'url': 'https://matchtv.ru/biathlon/matchtvvideo_NI1938496_translation_Letnij_biatlon_Alfa_Bank_Kubok_Sodruzhestva_Sprint_Muzhchiny',
        'md5': '0cb5e32169377d3022903b7776aae7a9',
        'info_dict': {
            'id': '20975a4cd84acdb55a0b5521277d0402',
            'ext': 'mp4',
            'title': 'Летний биатлон. Альфа-Банк Кубок Содружества. Спринт. Мужчины',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'МАТЧ ТВ',
            'description': 'md5:bc35a9942126e7463e779364c180b5f9',
            'duration': 7133.0,
            'upload_date': '20230907',
            'age_limit': 0,
            'timestamp': 1694071818,
        },
    }, {
        'url': 'https://matchtv.ru/biathlon/matchtvvideo_NI2100211_translation_Letnij_biatlon_Alfa_Bank_Kubok_Sodruzhestva_Sprint_Muzhchiny',
        'md5': '590a64c05257644d246f0db9ce294dd7',
        'info_dict': {
            'id': '65960e62d0d4f5bac535deab796f94a9',
            'ext': 'mp4',
            'title': 'Летний биатлон. Альфа-Банк Кубок Содружества. Спринт. Мужчины',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20240906',
            'duration': 7106.0,
            'timestamp': 1725612645,
            'uploader': 'МАТЧ ТВ',
            'age_limit': 0,
            'description': 'Летний биатлон. Альфа-Банк Кубок Содружества. Спринт. Мужчины',
        },
    }]
