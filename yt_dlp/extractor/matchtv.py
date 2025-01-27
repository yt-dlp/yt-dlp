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
    _VALID_URL = r'https?://bl\.video\.matchtv\.ru/(?:quote|media)/start/free_(?P<id>[^/]+)'
    _TESTS = []


class MatchTVFeedIE(WebcasterFeedBaseIE):
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://bl\.video\.matchtv\.ru/feed/start/free_(?P<id>[^/]+)'
    _TESTS = []
    _WEBPAGE_TESTS = [{
        'url': 'https://matchtv.ru/football/matchtvvideo_NI1593368_clip_Zolotoj_dubl_Cherchesova_Specialnyj_reportazh',
        'info_dict': {
            'id': '675ea0e4b4b1d54d21f9b52db6624199',
            'ext': 'mp4',
            'title': '«Золотой дубль Черчесова». Специальный репортаж',
            'thumbnail': r're:https?://[\w-]+.video.matchtv.ru/fc/[\w-]+/thumbnails/events/920749/135154185.jpg',
        },
    }, {
        'url': 'https://matchtv.ru/football/rossija/kubok_rossii/matchtvvideo_NI2100168_translation_FONBET_Kubok_Rossii_Tekstilshhik___Spartak_Kostroma',
        'info_dict': {
            'id': 'b6570efa80dc28df18523237d3f14a5b',
            'ext': 'mp4',
            'title': 'FONBET Кубок России по футболу сезона 2024 - 2025 гг. Текстильщик - Спартак Кострома',
            'thumbnail': r're:https?://[\w-]+.video.matchtv.ru/fc/[\w-]+/thumbnails/events/1202122/1039728778.jpg',
        },
    }, {
        'url': 'https://matchtv.ru/biathlon/matchtvvideo_NI1938496_translation_Letnij_biatlon_Alfa_Bank_Kubok_Sodruzhestva_Sprint_Muzhchiny',
        'info_dict': {
            'id': '20975a4cd84acdb55a0b5521277d0402',
            'ext': 'mp4',
            'title': 'Летний биатлон. Альфа-Банк Кубок Содружества. Спринт. Мужчины',
            'thumbnail': r're:https?://[\w-]+.video.matchtv.ru/fc/[\w-]+/thumbnails/events/1101266/590556538.jpg',
        },
    }]
