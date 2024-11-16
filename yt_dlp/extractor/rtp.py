import base64
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import js_to_json


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtp\.pt/play/(?:(?:estudoemcasa|palco|zigzag)/)?p(?P<program_id>[0-9]+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'http://www.rtp.pt/play/p405/e174042/paixoes-cruzadas',
        'md5': 'e736ce0c665e459ddb818546220b4ef8',
        'info_dict': {
            'id': 'e174042',
            'ext': 'mp3',
            'title': 'Paixões Cruzadas',
            'description': 'As paixões musicais de António Cartaxo e António Macedo',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'https://www.rtp.pt/play/zigzag/p13166/e757904/25-curiosidades-25-de-abril',
        'md5': '9a81ed53f2b2197cfa7ed455b12f8ade',
        'info_dict': {
            'id': 'e757904',
            'ext': 'mp4',
            'title': '25 Curiosidades, 25 de Abril',
            'description': 'Estudar ou não estudar - Em cada um dos episódios descobrimos uma curiosidade acerca de como era viver em Portugal antes da revolução do 25 de abr',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'http://www.rtp.pt/play/p831/a-quimica-das-coisas',
        'only_matching': True,
    }, {
        'url': 'https://www.rtp.pt/play/estudoemcasa/p7776/portugues-1-ano',
        'only_matching': True,
    }, {
        'url': 'https://www.rtp.pt/play/palco/p13785/l7nnon',
        'only_matching': True,
    }]

    _RX_OBFUSCATION = re.compile(r'''(?xs)
        atob\s*\(\s*decodeURIComponent\s*\(\s*
            (\[[0-9A-Za-z%,'"]*\])
        \s*\.\s*join\(\s*(?:""|'')\s*\)\s*\)\s*\)
    ''')

    def __unobfuscate(self, data, *, video_id):
        if data.startswith('{'):
            data = self._RX_OBFUSCATION.sub(
                lambda m: json.dumps(
                    base64.b64decode(urllib.parse.unquote(
                        ''.join(self._parse_json(m.group(1), video_id)),
                    )).decode('iso-8859-1')),
                data)
        return js_to_json(data)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        title = self._html_search_meta(
            'twitter:title', webpage, display_name='title', fatal=True)

        f, config = self._search_regex(
            r'''(?sx)
                (?:var\s+f\s*=\s*(?P<f>".*?"|{[^;]+?});\s*)?
                var\s+player1\s+=\s+new\s+RTPPlayer\s*\((?P<config>{(?:(?!\*/).)+?})\);(?!\s*\*/)
            ''', webpage,
            'player config', group=('f', 'config'))

        config = self._parse_json(
            config, video_id,
            lambda data: self.__unobfuscate(data, video_id=video_id))
        f = config['file'] if not f else self._parse_json(
            f, video_id,
            lambda data: self.__unobfuscate(data, video_id=video_id))

        formats = []
        if isinstance(f, dict):
            f_hls = f.get('hls')
            if f_hls is not None:
                formats.extend(self._extract_m3u8_formats(
                    f_hls, video_id, 'mp4', 'm3u8_native', m3u8_id='hls'))

            f_dash = f.get('dash')
            if f_dash is not None:
                formats.extend(self._extract_mpd_formats(f_dash, video_id, mpd_id='dash'))
        else:
            formats.append({
                'format_id': 'f',
                'url': f,
                'vcodec': 'none' if config.get('mediaType') == 'audio' else None,
            })

        subtitles = {}

        vtt = config.get('vtt')
        if vtt is not None:
            for lcode, lname, url in vtt:
                subtitles.setdefault(lcode, []).append({
                    'name': lname,
                    'url': url,
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': self._html_search_meta(['description', 'twitter:description'], webpage),
            'thumbnail': config.get('poster') or self._og_search_thumbnail(webpage),
            'subtitles': subtitles,
        }
