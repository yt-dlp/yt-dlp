import re
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


class DLFCorpusIE(DLFBaseIE):
    _VALID_URL = DLFBaseIE._VALID_URL_BASE + r'(?:[a-z]+-)+\d+\.html'

    IE_NAME = 'dlf:corpus'
    IE_DESC = 'DLF Multi-feed Archives'
    _TESTS = [
        # Recorded news broadcast with referrals to related broadcasts
        {
            'url': 'https://www.deutschlandfunk.de/fechten-russland-belarus-ukraine-protest-100.html',
            'info_dict': {
                'id': False,
                'title': r're:Wiederzulassung als neutrale Athleten [-/] Was die Rückkehr russischer und belarussischer Sportler beim Fechten bedeutet',
                'description': 'md5:91340aab29c71aa7518ad5be13d1e8ad'
            },
            'playlist': [{
                'info_dict': {
                    'id': '1fc5d64a',
                    'title': r're:Wiederzulassung als neutrale Athleten [-/] Was die Rückkehr russischer und belarussischer Sportler beim Fechten bedeutet',
                    'url': r're:https://(?:download\.deutschlandfunk|ondemand-mp3\.dradio)\.de/file/dradio/2023/03/22/rueckkehr_russischer_athleten_ukraine_will_fecht_wettbewerbe_dlf_20230322_1245_1fc5d64a\.mp3',
                    'ext': 'mp3',
                    'duration': 252,
                    'thumbnail': 'https://assets.deutschlandfunk.de/aad16241-6b76-4a09-958b-96d0ee1d6f57/512x512.jpg?t=1679480020313',
                    'uploader': 'Deutschlandfunk',
                    'series': 'Sport',
                    'channel': 'deutschlandfunk'
                }
            }, {
                'info_dict': {
                    'id': '2ada145f',
                    'title': r're:(?:Sportpolitik / )?Fechtverband votiert für Rückkehr russischer Athleten',
                    'url': r're:https://(?:download\.deutschlandfunk|ondemand-mp3\.dradio)\.de/file/dradio/2023/03/11/deutschlandfunknova_sportpolitik_fechtverband_20230311_2ada145f\.mp3',
                    'ext': 'mp3',
                    'duration': 336,
                    'thumbnail': 'https://assets.deutschlandfunk.de/FILE_93982766f7317df30409b8a184ac044a/512x512.jpg?t=1678547581005',
                    'uploader': 'Deutschlandfunk',
                    'series': 'Deutschlandfunk Nova',
                    'channel': 'deutschlandfunk-nova'
                }
            }, {
                'info_dict': {
                    'id': '5e55e8c9',
                    'title': r're:Wiederzulassung von Russland und Belarus [-/] "Herumlavieren" des Fechter-Bundes sorgt für Unverständnis',
                    'url': r're:https://(?:download\.deutschlandfunk|ondemand-mp3\.dradio)\.de/file/dradio/2023/03/18/fechten_unverstaendnis_und_wut_nach_wiederzulassung_dlf_20230318_1930_5e55e8c9\.mp3',
                    'ext': 'mp3',
                    'duration': 187,
                    'thumbnail': 'https://assets.deutschlandfunk.de/a595989d-1ed1-4a2e-8370-b64d7f11d757/512x512.jpg?t=1679173825412',
                    'uploader': 'Deutschlandfunk',
                    'series': 'Sport am Samstag',
                    'channel': 'deutschlandfunk'
                }
            }, {
                'info_dict': {
                    'id': '47e1a096',
                    'title': r're:Rückkehr Russlands im Fechten [-/] "Fassungslos, dass es einfach so passiert ist"',
                    'url': r're:https://(?:download\.deutschlandfunk|ondemand-mp3\.dradio)\.de/file/dradio/2023/03/11/weltfechtverband_laesst_russen_und_belarussen_wieder_zu_dlf_20230311_1912_47e1a096\.mp3',
                    'ext': 'mp3',
                    'duration': 602,
                    'thumbnail': 'https://assets.deutschlandfunk.de/da4c494a-21cc-48b4-9cc7-40e09fd442c2/512x512.jpg?t=1678562155770',
                    'uploader': 'Deutschlandfunk',
                    'series': 'Sport am Samstag',
                    'channel': 'deutschlandfunk'
                }
            }, {
                'info_dict': {
                    'id': '5e55e8c9',
                    'title': r're:Wiederzulassung von Russland und Belarus [-/] "Herumlavieren" des Fechter-Bundes sorgt für Unverständnis',
                    'url': r're:https://(?:download\.deutschlandfunk|ondemand-mp3\.dradio)\.de/file/dradio/2023/03/18/fechten_unverstaendnis_und_wut_nach_wiederzulassung_dlf_20230318_1930_5e55e8c9\.mp3',
                    'ext': 'mp3',
                    'duration': 187,
                    'thumbnail': 'https://assets.deutschlandfunk.de/a595989d-1ed1-4a2e-8370-b64d7f11d757/512x512.jpg?t=1679173825412',
                    'uploader': 'Deutschlandfunk',
                    'series': 'Sport am Samstag',
                    'channel': 'deutschlandfunk'
                }
            }],
            'params': {'skip_download': 'm3u8'}
        },
        # Podcast feed with tag buttons
        {
            'url': 'https://www.deutschlandfunk.de/corso-100.html',
            'info_dict': {
                'id': False,
                'title': r're:Kunst & Pop [-/] Corso',
                'description': 'md5:ba0f80303683591bff4b7459077bef58'
            },
            'playlist_mincount': 34,
            'params': {'skip_download': True}
        },
        # Podcast feed with no description
        {
            'url': 'https://www.deutschlandfunk.de/podcast-tolle-idee-100.html',
            'info_dict': {
                'id': False,
                'title': 'Wissenschaftspodcast - Tolle Idee! - Was wurde daraus?',
                'description': None
            },
            'playlist_mincount': 11,
            'params': {'skip_download': True}
        },
    ]

    def _real_extract(self, url):
        # Multi-feed pages do not embed an ID within the URL
        webpage = self._download_webpage(url, None)

        return {
            '_type': 'playlist',
            'id': False,
            'description': self._html_search_meta(
                ['description', 'og:description', 'twitter:description'], webpage, default=None),
            'title': self._html_search_meta(
                ['og:title', 'twitter:title'], webpage),
            'entries': [self._parse_button_attrs(button)
                        for button in re.findall(self._BUTTON_REGEX, webpage)],
        }
