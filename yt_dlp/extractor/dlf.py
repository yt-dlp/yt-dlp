import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    traverse_obj,
    url_or_none,
)


class DLFBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?deutschlandfunk\.de/'
    _BUTTON_REGEX = r'(<button[^>]+alt="Anhören"[^>]+data-audio-diraid[^>]*>)'

    def _parse_button_attrs(self, button, audio_id=None):
        attrs = extract_attributes(button)
        audio_id = audio_id or attrs['data-audio-diraid']

        url = traverse_obj(
            attrs, 'data-audio-download-src', 'data-audio', 'data-audioreference',
            'data-audio-src', expected_type=url_or_none)
        ext = determine_ext(url)

        return {
            'id': audio_id,
            'extractor_key': DLFIE.ie_key(),
            'extractor': DLFIE.IE_NAME,
            **traverse_obj(attrs, {
                'title': (('data-audiotitle', 'data-audio-title', 'data-audio-download-tracking-title'), {str}),
                'duration': (('data-audioduration', 'data-audio-duration'), {int_or_none}),
                'thumbnail': ('data-audioimage', {url_or_none}),
                'uploader': 'data-audio-producer',
                'series': 'data-audio-series',
                'channel': 'data-audio-origin-site-name',
                'webpage_url': ('data-audio-download-tracking-path', {url_or_none}),
            }, get_all=False),
            'formats': (self._extract_m3u8_formats(url, audio_id, fatal=False)
                        if ext == 'm3u8' else [{'url': url, 'ext': ext, 'vcodec': 'none'}])
        }


class DLFIE(DLFBaseIE):
    IE_NAME = 'dlf'
    _VALID_URL = DLFBaseIE._VALID_URL_BASE + r'[\w-]+-dlf-(?P<id>[\da-f]{8})-100\.html'
    _TESTS = [
        # Audio as an HLS stream
        {
            'url': 'https://www.deutschlandfunk.de/tanz-der-saiteninstrumente-das-wild-strings-trio-aus-slowenien-dlf-03a3eb19-100.html',
            'info_dict': {
                'id': '03a3eb19',
                'title': r're:Tanz der Saiteninstrumente [-/] Das Wild Strings Trio aus Slowenien',
                'ext': 'm4a',
                'duration': 3298,
                'thumbnail': 'https://assets.deutschlandfunk.de/FALLBACK-IMAGE-AUDIO/512x512.png?t=1603714364673',
                'uploader': 'Deutschlandfunk',
                'series': 'On Stage',
                'channel': 'deutschlandfunk'
            },
            'params': {
                'skip_download': 'm3u8'
            },
            'skip': 'This webpage no longer exists'
        }, {
            'url': 'https://www.deutschlandfunk.de/russische-athleten-kehren-zurueck-auf-die-sportbuehne-ein-gefaehrlicher-tueroeffner-dlf-d9cc1856-100.html',
            'info_dict': {
                'id': 'd9cc1856',
                'title': 'Russische Athleten kehren zurück auf die Sportbühne: Ein gefährlicher Türöffner',
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
        audio_id = self._match_id(url)
        webpage = self._download_webpage(url, audio_id)

        return self._parse_button_attrs(
            self._search_regex(self._BUTTON_REGEX, webpage, 'button'), audio_id)


class DLFCorpusIE(DLFBaseIE):
    IE_NAME = 'dlf:corpus'
    IE_DESC = 'DLF Multi-feed Archives'
    _VALID_URL = DLFBaseIE._VALID_URL_BASE + r'(?P<id>(?![\w-]+-dlf-[\da-f]{8})[\w-]+-\d+)\.html'
    _TESTS = [
        # Recorded news broadcast with referrals to related broadcasts
        {
            'url': 'https://www.deutschlandfunk.de/fechten-russland-belarus-ukraine-protest-100.html',
            'info_dict': {
                'id': 'fechten-russland-belarus-ukraine-protest-100',
                'title': r're:Wiederzulassung als neutrale Athleten [-/] Was die Rückkehr russischer und belarussischer Sportler beim Fechten bedeutet',
                'description': 'md5:91340aab29c71aa7518ad5be13d1e8ad'
            },
            'playlist_mincount': 5,
            'playlist': [{
                'info_dict': {
                    'id': '1fc5d64a',
                    'title': r're:Wiederzulassung als neutrale Athleten [-/] Was die Rückkehr russischer und belarussischer Sportler beim Fechten bedeutet',
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
                    'ext': 'mp3',
                    'duration': 187,
                    'thumbnail': 'https://assets.deutschlandfunk.de/a595989d-1ed1-4a2e-8370-b64d7f11d757/512x512.jpg?t=1679173825412',
                    'uploader': 'Deutschlandfunk',
                    'series': 'Sport am Samstag',
                    'channel': 'deutschlandfunk'
                }
            }]
        },
        # Podcast feed with tag buttons, playlist count fluctuates
        {
            'url': 'https://www.deutschlandfunk.de/kommentare-und-themen-der-woche-100.html',
            'info_dict': {
                'id': 'kommentare-und-themen-der-woche-100',
                'title': 'Meinung - Kommentare und Themen der Woche',
                'description': 'md5:2901bbd65cd2d45e116d399a099ce5d5',
            },
            'playlist_mincount': 10,
        },
        # Podcast feed with no description
        {
            'url': 'https://www.deutschlandfunk.de/podcast-tolle-idee-100.html',
            'info_dict': {
                'id': 'podcast-tolle-idee-100',
                'title': 'Wissenschaftspodcast - Tolle Idee! - Was wurde daraus?',
            },
            'playlist_mincount': 11,
        },
    ]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'description': self._html_search_meta(
                ['description', 'og:description', 'twitter:description'], webpage, default=None),
            'title': self._html_search_meta(
                ['og:title', 'twitter:title'], webpage, default=None),
            'entries': map(self._parse_button_attrs, re.findall(self._BUTTON_REGEX, webpage)),
        }
