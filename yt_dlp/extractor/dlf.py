from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    url_or_none,
)


class DLFBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?deutschlandfunk\.de/'
    _BUTTON_REGEX = r'(<button[^>]+alt="Anhören"[^>]+data-audio-diraid[^>]*>)'

    def _parse_button_attrs(self, button, id=None):
        attrs = extract_attributes(button)
        id = id or attrs['data-audio-diraid']

        # Note: DLF's mp3 recordings are in two distinct locations on the web:
        # A direct download location, https://download.deutschlandfunk.de/ ... .mp3
        # A stream with playback controls, https://ondemand-mp3.dradio.de/ ... .mp3
        url = url_or_none(
            attrs.get('data-audio-download-src')
            or attrs.get('data-audio')
            or attrs.get('data-audioreference')
            or attrs['data-audio-src'])

        return {
            'id': id,
            'title': (
                attrs.get('data-audiotitle')
                or attrs.get('data-audio-title')
                or attrs.get('data-audio-download-tracking-title')),
            'url': url,
            'formats': (
                self._extract_m3u8_formats(url, id) if determine_ext(url) == 'm3u8'
                else None),
            'duration': int_or_none(
                attrs.get('data-audioduration')
                or attrs.get('data-audio-duration')),
            'thumbnail': attrs.get('data-audioimage'),
            'uploader': attrs.get('data-audio-producer'),
            'series': attrs.get('data-audio-series'),
            'channel': attrs.get('data-audio-origin-site-name'),
        }


class DLFIE(DLFBaseIE):
    _VALID_URL = DLFBaseIE._VALID_URL_BASE + r'(?:\w+-)+(?P<id>[^-]*\d[^-]*)-100\.html'

    IE_NAME = 'dlf'
    _TESTS = [
        # Audio as an HLS stream
        {
            'url': 'https://www.deutschlandfunk.de/tanz-der-saiteninstrumente-das-wild-strings-trio-aus-slowenien-dlf-03a3eb19-100.html',
            'info_dict': {
                'id': '03a3eb19',
                'title': r're:Tanz der Saiteninstrumente [-/] Das Wild Strings Trio aus Slowenien',
                'url': 'https://dradiohls.akamaized.net/hls/2023/03/03/tanz_der_saiteninstrumente_das_wild_strings_trio_aus_dlf_20230303_2105_03a3eb19/128/seglist.m3u8',
                'ext': 'm4a',
                'duration': 3298,
                'thumbnail': 'https://assets.deutschlandfunk.de/FALLBACK-IMAGE-AUDIO/512x512.png?t=1603714364673',
                'uploader': 'Deutschlandfunk',
                'series': 'On Stage',
                'channel': 'deutschlandfunk'
            },
            'params': {
                'skip_download': 'm3u8'
            }
        }, {
            'url': 'https://www.deutschlandfunk.de/russische-athleten-kehren-zurueck-auf-die-sportbuehne-ein-gefaehrlicher-tueroeffner-dlf-d9cc1856-100.html',
            'info_dict': {
                'id': 'd9cc1856',
                'title': 'Russische Athleten kehren zurück auf die Sportbühne: Ein gefährlicher Türöffner',
                'url': r're:https://(download.deutschlandfunk|ondemand-mp3\.dradio)\.de/file/dradio/2023/04/01/russische_athleten_kehren_zurueck_auf_die_sportbuehne_ein_dlf_20230401_1905_d9cc1856\.mp3',
                'ext': 'mp3',
                'duration': 291,
                'thumbnail': 'https://assets.deutschlandfunk.de/FALLBACK-IMAGE-AUDIO/512x512.png?t=1603714364673',
                'uploader': 'Deutschlandfunk',
                'series': 'Kommentare und Themen der Woche',
                'channel': 'deutschlandfunk'
            }
        },
    ]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)

        return self._parse_button_attrs(
            self._search_regex(DLFBaseIE._BUTTON_REGEX, webpage, 'button'), id)
