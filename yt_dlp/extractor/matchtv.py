from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    join_nonempty,
    xpath_text,
)
from ..utils.traversal import traverse_obj


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


# WebcasterIE
class MatchTVVideoIE(InfoExtractor):
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://[.\w-]+/(?:quote|media)/start/free_(?P<id>[^/]+)'
    _TESTS = []

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_xml(url, video_id)

        title = xpath_text(video, './/event_name', 'event name', fatal=True)

        formats = []
        for format_id in (None, 'noise'):
            track_tag = join_nonempty('track', format_id, delim='_')
            for track in video.findall(f'.//iphone/{track_tag}'):
                track_url = track.text
                if not track_url:
                    continue
                if determine_ext(track_url) == 'm3u8':
                    m3u8_formats = self._extract_m3u8_formats(
                        track_url, video_id, 'mp4',
                        entry_protocol='m3u8_native',
                        m3u8_id=join_nonempty('hls', format_id, delim='-'), fatal=False)
                    for f in m3u8_formats:
                        f.update({
                            'source_preference': 0 if format_id == 'noise' else 1,
                            'format_note': track.get('title'),
                        })
                    formats.extend(m3u8_formats)

        thumbnail = xpath_text(video, './/image', 'thumbnail')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }


# WebcasterFeedIE
class MatchTVFeedIE(InfoExtractor):
    _GEO_COUNTRIES = ['RU']
    _VALID_URL = r'https?://[.\w-]+/feed/start/free_(?P<id>[^/]+)'
    _EMBED_REGEX = [r'<(?:object|a|span[^>]+class=["\']webcaster-player["\'])[^>]+data(?:-config)?=(["\']).*?config=(?P<url>https?://(?:(?!\1).)+)\1']
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

    def _extract_from_webpage(self, url, webpage):
        yield from super()._extract_from_webpage(url, webpage)

        yield from traverse_obj(self._yield_json_ld(webpage, None), (
            lambda _, v: v['@type'] == 'VideoObject', 'url',
            {extract_attributes}, 'src', {self.url_result}))

    def _real_extract(self, url):
        video_id = self._match_id(url)

        feed = self._download_xml(url, video_id)

        video_url = xpath_text(
            feed, ('video_hd', 'video'), 'video url', fatal=True)

        return self.url_result(video_url)
