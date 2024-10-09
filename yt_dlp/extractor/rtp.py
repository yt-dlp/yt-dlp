import base64
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import ExtractorError, determine_ext, join_nonempty


def decode_b64_url(code):
    decoded_url = re.match(r'[^[]*\[([^]]*)\]', code).groups()[0]
    return base64.b64decode(
        urllib.parse.unquote(re.sub(r'[\s"\',]', '', decoded_url)),
    ).decode('utf-8')


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:(?:www\.)?rtp\.pt/play/(?P<subarea>.*/)?p(?P<program_id>[0-9]+)/(?P<episode_id>e[0-9]+/)?)|(?:arquivos\.rtp\.pt/conteudos/))(?P<id>[^/?#]+)/?'
    _TESTS = [{
        'url': 'https://www.rtp.pt/play/p9165/e562949/por-do-sol',
        'info_dict': {
            'id': 'por-do-sol',
            'ext': 'mp4',
            'title': 'Pôr do Sol Episódio 1 - de 16 Ago 2021',
            'description': 'Madalena Bourbon de Linhaça vive atormentada pelo segredo que esconde desde 1990. Matilde Bourbon de Linhaça sonha fugir com o seu amor proibido. O en',
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
        'url': 'https://www.rtp.pt/play/p831/e205093/a-quimica-das-coisas',
        'only_matching': True,
    }, {
        'url': 'https://www.rtp.pt/play/estudoemcasa/p7776/e500050/portugues-1-ano',
        'only_matching': True,
    }, {
        'url': 'https://www.rtp.pt/play/palco/p9138/jose-afonso-traz-um-amigo-tambem',
        'only_matching': True,
    }, {
        'url': 'https://www.rtp.pt/play/p510/e798152/aleixo-fm',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        # Remove comments from webpage source
        webpage = re.sub(r'(?s)/\*.*\*/', '', webpage)
        webpage = re.sub(r'(?m)(?:^|\s)//.*$', '', webpage)

        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title', default='')
        # Replace irrelevant text in title
        title = title.replace(' - RTP Play - RTP', '') or self._html_search_meta('twitter:title', webpage)

        if 'Este episódio não se encontra disponí' in title:
            raise ExtractorError('Episode unavailable', expected=True)

        part = self._html_search_regex(r'section\-parts.*<span.*>(.+?)</span>.*</ul>', webpage, 'part', default=None)
        title = join_nonempty(title, part, delim=' ')

        # Get file key
        file_key = self._search_regex(r'\s*fileKey: "([^"]+)",', webpage, 'file key - open', default=None)
        if file_key is None:
            self.write_debug('url: obfuscated')
            file_key = self._search_regex(r'\s*fileKey: atob\( decodeURIComponent\((.*)\)\)\),', webpage, 'file key')
            url = decode_b64_url(file_key) or ''
        else:
            self.write_debug('url: clean')
            url = file_key

        if 'mp3' in url:
            full_url = 'https://cdn-ondemand.rtp.pt' + url
        elif 'mp4' in url:
            full_url = f'https://streaming-vod.rtp.pt/dash{url}/manifest.mpd'
        else:
            full_url = None

        if not full_url:
            raise ExtractorError('No valid media source found in page')

        poster = self._search_regex(r'\s*poster: "([^"]+)"', webpage, 'poster', fatal=False)

        # Finally send pure JSON string for JSON parsing
        full_url = full_url.replace('drm-dash', 'dash')
        ext = determine_ext(full_url)

        if ext == 'mpd':
            # Download via mpd file
            self.write_debug('formats: mpd')
            formats = self._extract_mpd_formats(full_url, video_id)
        else:
            self.write_debug('formats: ext={ext}')
            formats = [{
                'url': full_url,
                'ext': ext,
            }]

        subtitles = {}
        vtt = self._search_regex(r'\s*vtt: (.*]]),\s+', webpage, 'vtt', default=None)
        if vtt is not None:
            vtt_object = self._parse_json(vtt.replace("'", '"'), full_url)
            self.write_debug(f'vtt: {len(vtt_object)} subtitles')
            for lcode, lname, url in vtt_object:
                subtitles.setdefault(lcode.lower(), []).append({
                    'name': lname,
                    'url': url,
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': self._html_search_meta(['description', 'twitter:description'], webpage),
            'thumbnail': poster or self._og_search_thumbnail(webpage),
            'subtitles': subtitles,
        }
