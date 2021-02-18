# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    js_to_json,
    qualities,
    determine_ext,
)


class Tele13IE(InfoExtractor):
    _VALID_URL = r'^https?://(?:www\.)?t13\.cl/videos(?:/[^/]+)+/(?P<id>[\w-]+)'
    _TESTS = [
        {
            'url': 'http://www.t13.cl/videos/actualidad/el-circulo-de-hierro-de-michelle-bachelet-en-su-regreso-a-la-moneda',
            'md5': '4cb1fa38adcad8fea88487a078831755',
            'info_dict': {
                'id': 'el-circulo-de-hierro-de-michelle-bachelet-en-su-regreso-a-la-moneda',
                'ext': 'mp4',
                'title': 'El círculo de hierro de Michelle Bachelet en su regreso a La Moneda',
            },
            'params': {
                # HTTP Error 404: Not Found
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.t13.cl/videos/mundo/tendencias/video-captan-misteriosa-bola-fuego-cielos-bangkok',
            'md5': '867adf6a3b3fef932c68a71d70b70946',
            'info_dict': {
                'id': 'rOoKv2OMpOw',
                'ext': 'mp4',
                'title': 'Shooting star seen on 7-Sep-2015',
                'description': 'md5:7292ff2a34b2f673da77da222ae77e1e',
                'uploader': 'Porjai Jaturongkhakun',
                'upload_date': '20150906',
                'uploader_id': 'UCnLY_3ezwNcDSC_Wc6suZxw',
            },
            'add_ie': ['Youtube'],
        }
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        setup_js = self._search_regex(
            r"(?s)jwplayer\('player-vivo'\).setup\((\{.*?\})\)",
            webpage, 'setup code')
        sources = self._parse_json(self._search_regex(
            r'sources\s*:\s*(\[[^\]]+\])', setup_js, 'sources'),
            display_id, js_to_json)

        preference = qualities(['Móvil', 'SD', 'HD'])
        formats = []
        urls = []
        for f in sources:
            format_url = f['file']
            if format_url and format_url not in urls:
                ext = determine_ext(format_url)
                if ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, display_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls', fatal=False))
                elif YoutubeIE.suitable(format_url):
                    return self.url_result(format_url, 'Youtube')
                else:
                    formats.append({
                        'url': format_url,
                        'format_id': f.get('label'),
                        'quality': preference(f.get('label')),
                        'ext': ext,
                    })
                urls.append(format_url)
        self._sort_formats(formats)

        return {
            'id': display_id,
            'title': self._search_regex(
                r'title\s*:\s*"([^"]+)"', setup_js, 'title'),
            'description': self._html_search_meta(
                'description', webpage, 'description'),
            'thumbnail': self._search_regex(
                r'image\s*:\s*"([^"]+)"', setup_js, 'thumbnail', default=None),
            'formats': formats,
        }
