import base64
import io
import struct
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    InAdvancePagedList,
    clean_html,
    determine_ext,
    float_or_none,
    int_or_none,
    make_archive_id,
    parse_iso8601,
    qualities,
    url_or_none,
)
from ..utils.traversal import subs_list_to_dict, traverse_obj


class RTVEBaseIE(InfoExtractor):
    # Reimplementation of https://js2.rtve.es/pages/app-player/3.5.1/js/pf_video.js
    @staticmethod
    def _decrypt_url(png):
        encrypted_data = io.BytesIO(base64.b64decode(png)[8:])
        while True:
            length_data = encrypted_data.read(4)
            length = struct.unpack('!I', length_data)[0]
            chunk_type = encrypted_data.read(4)
            if chunk_type == b'IEND':
                break
            data = encrypted_data.read(length)
            if chunk_type == b'tEXt':
                data = bytes(filter(None, data))
                alphabet_data, _, url_data = data.partition(b'#')
                quality_str, _, url_data = url_data.rpartition(b'%%')
                quality_str = quality_str.decode() or ''
                alphabet = RTVEBaseIE._get_alphabet(alphabet_data)
                url = RTVEBaseIE._get_url(alphabet, url_data)
                yield quality_str, url
            encrypted_data.read(4)  # CRC

    @staticmethod
    def _get_url(alphabet, url_data):
        url = ''
        f = 0
        e = 3
        b = 1
        for char in url_data.decode('iso-8859-1'):
            if f == 0:
                l = int(char) * 10
                f = 1
            else:
                if e == 0:
                    l += int(char)
                    url += alphabet[l]
                    e = (b + 3) % 4
                    f = 0
                    b += 1
                else:
                    e -= 1
        return url

    @staticmethod
    def _get_alphabet(alphabet_data):
        alphabet = []
        e = 0
        d = 0
        for char in alphabet_data.decode('iso-8859-1'):
            if d == 0:
                alphabet.append(char)
                d = e = (e + 1) % 4
            else:
                d -= 1
        return alphabet

    def _extract_png_formats_and_subtitles(self, video_id, media_type='videos'):
        formats, subtitles = [], {}
        q = qualities(['Media', 'Alta', 'HQ', 'HD_READY', 'HD_FULL'])
        for manager in ('rtveplayw', 'default'):
            png = self._download_webpage(
                f'http://www.rtve.es/ztnr/movil/thumbnail/{manager}/{media_type}/{video_id}.png',
                video_id, 'Downloading url information', query={'q': 'v2'}, fatal=False)
            if not png:
                continue

            for quality, video_url in self._decrypt_url(png):
                ext = determine_ext(video_url)
                if ext == 'm3u8':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        video_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                elif ext == 'mpd':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(
                        video_url, video_id, 'dash', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                else:
                    formats.append({
                        'format_id': quality,
                        'quality': q(quality),
                        'url': video_url,
                    })
        return formats, subtitles

    def _parse_metadata(self, metadata):
        return traverse_obj(metadata, {
            'title': ('title', {str.strip}),
            'alt_title': ('alt', {str.strip}),
            'description': ('description', {clean_html}),
            'timestamp': ('dateOfEmission', {parse_iso8601(delimiter=' ')}),
            'release_timestamp': ('publicationDate', {parse_iso8601(delimiter=' ')}),
            'modified_timestamp': ('modificationDate', {parse_iso8601(delimiter=' ')}),
            'thumbnail': (('thumbnail', 'image', 'imageSEO'), {url_or_none}, any),
            'duration': ('duration', {float_or_none(scale=1000)}),
            'is_live': ('live', {bool}),
            'series': (('programTitle', ('programInfo', 'title')), {clean_html}, any),
        })


class RTVEALaCartaIE(RTVEBaseIE):
    IE_NAME = 'rtve.es:alacarta'
    IE_DESC = 'RTVE a la carta and Play'
    _VALID_URL = [
        r'https?://(?:www\.)?rtve\.es/(?:m/)?(?:(?:alacarta|play)/videos|filmoteca)/(?!directo)(?:[^/?#]+/){2}(?P<id>\d+)',
        r'https?://(?:www\.)?rtve\.es/infantil/serie/[^/?#]+/video/[^/?#]+/(?P<id>\d+)',
    ]

    _TESTS = [{
        'url': 'http://www.rtve.es/alacarta/videos/la-aventura-del-saber/aventuraentornosilla/3088905/',
        'md5': 'a964547824359a5753aef09d79fe984b',
        'info_dict': {
            'id': '3088905',
            'ext': 'mp4',
            'title': 'En torno a la silla',
            'duration': 1216.981,
            'series': 'La aventura del Saber',
            'thumbnail': 'https://img2.rtve.es/v/aventuraentornosilla_3088905.png',
        },
    }, {
        'note': 'Live stream',
        'url': 'http://www.rtve.es/alacarta/videos/television/24h-live/1694255/',
        'info_dict': {
            'id': '1694255',
            'ext': 'mp4',
            'title': 're:^24H LIVE [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'is_live': True,
            'live_status': 'is_live',
            'thumbnail': r're:https://img2\.rtve\.es/v/.*\.png',
        },
        'params': {
            'skip_download': 'live stream',
        },
    }, {
        'url': 'http://www.rtve.es/alacarta/videos/servir-y-proteger/servir-proteger-capitulo-104/4236788/',
        'md5': 'f3cf0d1902d008c48c793e736706c174',
        'info_dict': {
            'id': '4236788',
            'ext': 'mp4',
            'title': 'Episodio 104',
            'duration': 3222.8,
            'thumbnail': r're:https://img2\.rtve\.es/v/.*\.png',
            'series': 'Servir y proteger',
        },
    }, {
        'url': 'http://www.rtve.es/m/alacarta/videos/cuentame-como-paso/cuentame-como-paso-t16-ultimo-minuto-nuestra-vida-capitulo-276/2969138/?media=tve',
        'only_matching': True,
    }, {
        'url': 'http://www.rtve.es/filmoteca/no-do/not-1-introduccion-primer-noticiario-espanol/1465256/',
        'only_matching': True,
    }, {
        'url': 'https://www.rtve.es/play/videos/saber-vivir/07-07-24/16177116/',
        'md5': 'a5b24fcdfa3ff5cb7908aba53d22d4b6',
        'info_dict': {
            'id': '16177116',
            'ext': 'mp4',
            'title': 'Saber vivir - 07/07/24',
            'thumbnail': r're:https://img2\.rtve\.es/v/.*\.png',
            'duration': 2162.68,
            'series': 'Saber vivir',
        },
    }, {
        'url': 'https://www.rtve.es/infantil/serie/agus-lui-churros-crafts/video/gusano/7048976/',
        'info_dict': {
            'id': '7048976',
            'ext': 'mp4',
            'title': 'Gusano',
            'thumbnail': r're:https://img2\.rtve\.es/v/.*\.png',
            'duration': 292.86,
            'series': 'Agus & Lui: Churros y Crafts',
            '_old_archive_ids': ['rtveinfantil 7048976'],
        },
    }]

    def _get_subtitles(self, video_id):
        subtitle_data = self._download_json(
            f'https://api2.rtve.es/api/videos/{video_id}/subtitulos.json', video_id,
            'Downloading subtitles info')
        return traverse_obj(subtitle_data, ('page', 'items', ..., {
            'id': ('lang', {str}),
            'url': ('src', {url_or_none}),
        }, all, {subs_list_to_dict(lang='es')}))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(
            f'http://www.rtve.es/api/videos/{video_id}/config/alacarta_videos.json',
            video_id)['page']['items'][0]
        if metadata['state'] == 'DESPU':
            raise ExtractorError('The video is no longer available', expected=True)
        formats, subtitles = self._extract_png_formats_and_subtitles(video_id)

        self._merge_subtitles(self.extract_subtitles(video_id), target=subtitles)

        is_infantil = urllib.parse.urlparse(url).path.startswith('/infantil/')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **self._parse_metadata(metadata),
            '_old_archive_ids': [make_archive_id('rtveinfantil', video_id)] if is_infantil else None,
        }


class RTVEAudioIE(RTVEBaseIE):
    IE_NAME = 'rtve.es:audio'
    IE_DESC = 'RTVE audio'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/(alacarta|play)/audios/(?:[^/?#]+/){2}(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.rtve.es/alacarta/audios/a-hombros-de-gigantes/palabra-ingeniero-codigos-informaticos-27-04-21/5889192/',
        'md5': 'ae06d27bff945c4e87a50f89f6ce48ce',
        'info_dict': {
            'id': '5889192',
            'ext': 'mp3',
            'title': 'Códigos informáticos',
            'alt_title': 'Códigos informáticos - Escuchar ahora',
            'duration': 349.440,
            'series': 'A hombros de gigantes',
            'description': 'md5:72b0d7c1ca20fd327bdfff7ac0171afb',
            'thumbnail': 'https://img2.rtve.es/a/palabra-ingeniero-codigos-informaticos-270421_5889192.png',
        },
    }, {
        'url': 'https://www.rtve.es/play/audios/en-radio-3/ignatius-farray/5791165/',
        'md5': '072855ab89a9450e0ba314c717fa5ebc',
        'info_dict': {
            'id': '5791165',
            'ext': 'mp3',
            'title': 'Ignatius Farray',
            'alt_title': 'En Radio 3 - Ignatius Farray - 13/02/21 - escuchar ahora',
            'thumbnail': r're:https?://.+/1613243011863.jpg',
            'duration': 3559.559,
            'series': 'En Radio 3',
            'description': 'md5:124aa60b461e0b1724a380bad3bc4040',
        },
    }, {
        'url': 'https://www.rtve.es/play/audios/frankenstein-o-el-moderno-prometeo/capitulo-26-ultimo-muerte-victor-juan-jose-plans-mary-shelley/6082623/',
        'md5': '0eadab248cc8dd193fa5765712e84d5c',
        'info_dict': {
            'id': '6082623',
            'ext': 'mp3',
            'title': 'Capítulo 26 y último: La muerte de Victor',
            'alt_title': 'Frankenstein o el moderno Prometeo - Capítulo 26 y último: La muerte de Victor',
            'thumbnail': r're:https?://.+/1632147445707.jpg',
            'duration': 3174.086,
            'series': 'Frankenstein o el moderno Prometeo',
            'description': 'md5:4ee6fcb82ebe2e46d267e1d1c1a8f7b5',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        metadata = self._download_json(
            f'https://www.rtve.es/api/audios/{audio_id}.json', audio_id)['page']['items'][0]

        formats, subtitles = self._extract_png_formats_and_subtitles(audio_id, media_type='audios')

        return {
            'id': audio_id,
            'formats': formats,
            'subtitles': subtitles,
            **self._parse_metadata(metadata),
        }


class RTVELiveIE(RTVEBaseIE):
    IE_NAME = 'rtve.es:live'
    IE_DESC = 'RTVE.es live streams'
    _VALID_URL = [
        r'https?://(?:www\.)?rtve\.es/directo/(?P<id>[a-zA-Z0-9-]+)',
        r'https?://(?:www\.)?rtve\.es/play/videos/directo/[^/?#]+/(?P<id>[a-zA-Z0-9-]+)',
    ]

    _TESTS = [{
        'url': 'http://www.rtve.es/directo/la-1/',
        'info_dict': {
            'id': 'la-1',
            'ext': 'mp4',
            'live_status': 'is_live',
            'title': str,
            'description': str,
            'thumbnail': r're:https://img\d\.rtve\.es/resources/thumbslive/\d+\.jpg',
            'timestamp': int,
            'upload_date': str,
        },
        'params': {'skip_download': 'live stream'},
    }, {
        'url': 'https://www.rtve.es/play/videos/directo/deportes/tdp/',
        'info_dict': {
            'id': 'tdp',
            'ext': 'mp4',
            'live_status': 'is_live',
            'title': str,
            'description': str,
            'thumbnail': r're:https://img2\d\.rtve\.es/resources/thumbslive/\d+\.jpg',
            'timestamp': int,
            'upload_date': str,
        },
        'params': {'skip_download': 'live stream'},
    }, {
        'url': 'http://www.rtve.es/play/videos/directo/canales-lineales/la-1/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data_setup = self._search_json(
            r'<div[^>]+class="[^"]*videoPlayer[^"]*"[^>]*data-setup=\'',
            webpage, 'data_setup', video_id)

        formats, subtitles = self._extract_png_formats_and_subtitles(data_setup['idAsset'])

        return {
            'id': video_id,
            **self._search_json_ld(webpage, video_id, fatal=False),
            'title': self._html_extract_title(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
        }


class RTVETelevisionIE(InfoExtractor):
    IE_NAME = 'rtve.es:television'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/television/[^/?#]+/[^/?#]+/(?P<id>\d+).shtml'

    _TEST = {
        'url': 'https://www.rtve.es/television/20091103/video-inedito-del-8o-programa/299020.shtml',
        'info_dict': {
            'id': '572515',
            'ext': 'mp4',
            'title': 'Clase inédita',
            'duration': 335.817,
            'thumbnail': r're:https://img2\.rtve\.es/v/.*\.png',
            'series': 'El coro de la cárcel',
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        play_url = self._html_search_meta('contentUrl', webpage)
        if play_url is None:
            raise ExtractorError('The webpage doesn\'t contain any video', expected=True)

        return self.url_result(play_url, ie=RTVEALaCartaIE.ie_key())


class RTVEProgramIE(RTVEBaseIE):
    IE_NAME = 'rtve.es:program'
    IE_DESC = 'RTVE.es programs'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/play/videos/(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.rtve.es/play/videos/saber-vivir/',
        'info_dict': {
            'id': '111570',
            'title': 'Saber vivir - Programa de ciencia y futuro en RTVE Play',
        },
        'playlist_mincount': 400,
    }]
    _PAGE_SIZE = 60

    def _fetch_page(self, program_id, page_num):
        return self._download_json(
            f'https://www.rtve.es/api/programas/{program_id}/videos',
            program_id, note=f'Downloading page {page_num}',
            query={
                'type': 39816,
                'page': page_num,
                'size': 60,
            })

    def _entries(self, page_data):
        for video in traverse_obj(page_data, ('page', 'items', lambda _, v: url_or_none(v['htmlUrl']))):
            yield self.url_result(
                video['htmlUrl'], RTVEALaCartaIE, url_transparent=True,
                **traverse_obj(video, {
                    'id': ('id', {str}),
                    'title': ('longTitle', {str}),
                    'description': ('shortDescription', {str}),
                    'duration': ('duration', {float_or_none(scale=1000)}),
                    'series': (('programInfo', 'title'), {str}, any),
                    'season_number': ('temporadaOrden', {int_or_none}),
                    'season_id': ('temporadaId', {str}),
                    'season': ('temporada', {str}),
                    'episode_number': ('episode', {int_or_none}),
                    'episode': ('title', {str}),
                    'thumbnail': ('thumbnail', {url_or_none}),
                }),
            )

    def _real_extract(self, url):
        program_slug = self._match_id(url)
        program_page = self._download_webpage(url, program_slug)

        program_id = self._html_search_meta('DC.identifier', program_page, 'Program ID', fatal=True)

        first_page = self._fetch_page(program_id, 1)
        page_count = traverse_obj(first_page, ('page', 'totalPages', {int})) or 1

        entries = InAdvancePagedList(
            lambda idx: self._entries(self._fetch_page(program_id, idx + 1) if idx else first_page),
            page_count, self._PAGE_SIZE)

        return self.playlist_result(entries, program_id, self._html_extract_title(program_page))
