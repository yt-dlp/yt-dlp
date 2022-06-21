import re

from .common import InfoExtractor
from ..utils import js_to_json


class RTNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rt\.com/[^/]+/(?:[^/]+/)?(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.rt.com/sport/546301-djokovic-arrives-belgrade-crowds/',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '546301',
            'title': 'Crowds gather to greet deported Djokovic as he returns to Serbia (VIDEO)',
            'description': 'md5:1d5bfe1a988d81fd74227cfdf93d314d',
            'thumbnail': 'https://cdni.rt.com/files/2022.01/article/61e587a085f540102c3386c1.png'
        },
    }, {
        'url': 'https://www.rt.com/shows/in-question/535980-plot-to-assassinate-julian-assange/',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '535980',
            'title': 'The plot to assassinate Julian Assange',
            'description': 'md5:55279ce5e4441dc1d16e2e4a730152cd',
            'thumbnail': 'https://cdni.rt.com/files/2021.09/article/615226f42030274e8879b53d.png'
        },
        'playlist': [{
            'info_dict': {
                'id': '6152271d85f5400464496162',
                'ext': 'mp4',
                'title': '6152271d85f5400464496162',
            },
        }]
    }]

    def _entries(self, webpage):
        video_urls = set(re.findall(r'https://cdnv\.rt\.com/.*[a-f0-9]+\.mp4', webpage))
        for v_url in video_urls:
            v_id = re.search(r'([a-f0-9]+)\.mp4', v_url).group(1)
            if v_id:
                yield {
                    'id': v_id,
                    'title': v_id,
                    'url': v_url,
                }

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)

        return {
            '_type': 'playlist',
            'id': id,
            'entries': self._entries(webpage),
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
        }


class RTDocumentryIE(InfoExtractor):
    _VALID_URL = r'https?://rtd\.rt\.com/(?:(?:series|shows)/[^/]+|films)/(?P<id>[^/?$&#]+)'

    _TESTS = [{
        'url': 'https://rtd.rt.com/films/escobars-hitman/',
        'info_dict': {
            'id': 'escobars-hitman',
            'ext': 'mp4',
            'title': "Escobar's Hitman. Former drug-gang killer, now loved and loathed in Colombia",
            'description': 'md5:647c76984b7cb9a8b52a567e87448d88',
            'thumbnail': 'https://cdni.rt.com/rtd-files/films/escobars-hitman/escobars-hitman_11.jpg',
            'average_rating': 8.53,
            'duration': 3134.0
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://rtd.rt.com/shows/the-kalashnikova-show-military-secrets-anna-knishenko/iskander-tactical-system-natos-headache/',
        'info_dict': {
            'id': 'iskander-tactical-system-natos-headache',
            'ext': 'mp4',
            'title': "Iskander tactical system. NATO's headache | The Kalashnikova Show. Episode 10",
            'description': 'md5:da7c24a0aa67bc2bb88c86658508ca87',
            'thumbnail': 'md5:89de8ce38c710b7c501ff02d47e2aa89',
            'average_rating': 9.27,
            'duration': 274.0,
            'timestamp': 1605726000,
            'view_count': int,
            'upload_date': '20201118'
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://rtd.rt.com/series/i-am-hacked-trailer/introduction-to-safe-digital-life-ep2/',
        'info_dict': {
            'id': 'introduction-to-safe-digital-life-ep2',
            'ext': 'mp4',
            'title': 'How to Keep your Money away from Hackers | I am Hacked. Episode 2',
            'description': 'md5:c46fa9a5af86c0008c45a3940a8cce87',
            'thumbnail': 'md5:a5e81b9bf5aed8f5e23d9c053601b825',
            'average_rating': 10.0,
            'duration': 1524.0,
            'timestamp': 1636977600,
            'view_count': int,
            'upload_date': '20211115'
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        ld_json = self._search_json_ld(webpage, None, fatal=False)
        if not ld_json:
            self.raise_no_formats('No video/audio found at the provided url.', expected=True)
        media_json = self._parse_json(
            self._search_regex(r'(?s)\'Med\'\s*:\s*\[\s*({.+})\s*\]\s*};', webpage, 'media info'),
            id, transform_source=js_to_json)
        if 'title' not in ld_json and 'title' in media_json:
            ld_json['title'] = media_json['title']
        formats = [{'url': src['file']} for src in media_json.get('sources') or [] if src.get('file')]

        return {
            'id': id,
            'thumbnail': media_json.get('image'),
            'formats': formats,
            **ld_json
        }


class RTDocumentryPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://rtd\.rt\.com/(?:series|shows)/(?P<id>[^/]+)/$'

    _TESTS = [{
        'url': 'https://rtd.rt.com/series/i-am-hacked-trailer/',
        'playlist_mincount': 6,
        'info_dict': {
            'id': 'i-am-hacked-trailer',
        },
    }, {
        'url': 'https://rtd.rt.com/shows/the-kalashnikova-show-military-secrets-anna-knishenko/',
        'playlist_mincount': 34,
        'info_dict': {
            'id': 'the-kalashnikova-show-military-secrets-anna-knishenko',
        },
    }]

    def _entries(self, webpage, id):
        video_urls = set(re.findall(r'list-2__link\s*"\s*href="([^"]+)"', webpage))
        for v_url in video_urls:
            if id not in v_url:
                continue
            yield self.url_result(
                'https://rtd.rt.com%s' % v_url,
                ie=RTDocumentryIE.ie_key())

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)

        return {
            '_type': 'playlist',
            'id': id,
            'entries': self._entries(webpage, id),
        }


class RuptlyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ruptly\.tv/[a-z]{2}/videos/(?P<id>\d+-\d+)'

    _TESTS = [{
        'url': 'https://www.ruptly.tv/en/videos/20220112-020-Japan-Double-trouble-Tokyo-zoo-presents-adorable-panda-twins',
        'info_dict': {
            'id': '20220112-020',
            'ext': 'mp4',
            'title': 'Japan: Double trouble! Tokyo zoo presents adorable panda twins | Video Ruptly',
            'description': 'md5:85a8da5fdb31486f0562daf4360ce75a',
            'thumbnail': 'https://storage.ruptly.tv/thumbnails/20220112-020/i6JQKnTNpYuqaXsR/i6JQKnTNpYuqaXsR.jpg'
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        m3u8_url = self._search_regex(r'preview_url"\s?:\s?"(https?://storage\.ruptly\.tv/video_projects/.+\.m3u8)"', webpage, 'm3u8 url', fatal=False)
        if not m3u8_url:
            self.raise_no_formats('No video/audio found at the provided url.', expected=True)
        formats, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, id, ext='mp4')
        return {
            'id': id,
            'formats': formats,
            'subtitles': subs,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
        }
