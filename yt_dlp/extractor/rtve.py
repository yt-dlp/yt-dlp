import base64
import io
import struct

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    qualities,
    try_get,
)


class RTVEALaCartaIE(InfoExtractor):
    IE_NAME = 'rtve.es:alacarta'
    IE_DESC = 'RTVE a la carta and Play'
    _VALID_URL = [
        r'https?://(?:www\.)?rtve\.es/(m/)?(alacarta/videos|filmoteca)/[^/]+/[^/]+/(?P<id>\d+)',
        r'https?://(?:www\.)?rtve\.es/(m/)?play/videos/[^/]+/[^/]+/(?P<id>\d+)',
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
        'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
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
        'expected_warnings': ['Failed to download MPD manifest', 'Failed to download m3u8 information'],
    }, {
        'url': 'http://www.rtve.es/m/alacarta/videos/cuentame-como-paso/cuentame-como-paso-t16-ultimo-minuto-nuestra-vida-capitulo-276/2969138/?media=tve',
        'only_matching': True,
    }, {
        'url': 'http://www.rtve.es/filmoteca/no-do/not-1-introduccion-primer-noticiario-espanol/1465256/',
        'only_matching': True,
    }, {
        'url': 'https://www.rtve.es/play/videos/saber-vivir/07-07-24/16177116/',
        'md5': '9eebcf6e8d6306c3b7c46e86a0115f55',
        'info_dict': {
            'id': '16177116',
            'ext': 'mp4',
            'title': 'Saber vivir - 07/07/24',
            'thumbnail': r're:https://img2\.rtve\.es/v/.*\.png',
            'duration': 2162.68,
            'series': 'Saber vivir',
        },
        'expected_warnings': ['Failed to download MPD manifest', 'Failed to download m3u8 information'],
    }]

    def _real_initialize(self):
        user_agent_b64 = base64.b64encode(self.get_param('http_headers')['User-Agent'].encode()).decode('utf-8')
        self._manager = self._download_json(
            'http://www.rtve.es/odin/loki/' + user_agent_b64,
            None, 'Fetching manager info')['manager']

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
                if b'%%' in data:
                    alphabet_data, text = data.split(b'\0')
                    quality, url_data = text.split(b'%%')
                    alphabet = RTVEALaCartaIE._get_alfabet(alphabet_data)
                    url = RTVEALaCartaIE._get_url(alphabet, url_data)
                    quality_str = quality.decode()
                else:
                    data = bytes(filter(None, data))
                    alphabet_data, url_data = data.split(b'#')
                    alphabet = RTVEALaCartaIE._get_alfabet(alphabet_data)

                    url = RTVEALaCartaIE._get_url(alphabet, url_data)
                    quality_str = ''
                yield quality_str, url
            encrypted_data.read(4)  # CRC

    @staticmethod
    def _get_url(alphabet, url_data):
        url = ''
        f = 0
        e = 3
        b = 1
        for letter in url_data.decode('iso-8859-1'):
            if f == 0:
                l = int(letter) * 10
                f = 1
            else:
                if e == 0:
                    l += int(letter)
                    url += alphabet[l]
                    e = (b + 3) % 4
                    f = 0
                    b += 1
                else:
                    e -= 1
        return url

    @staticmethod
    def _get_alfabet(alphabet_data):
        alphabet = []
        e = 0
        d = 0
        for l in alphabet_data.decode('iso-8859-1'):
            if d == 0:
                alphabet.append(l)
                d = e = (e + 1) % 4
            else:
                d -= 1
        return alphabet

    def _extract_png_formats(self, video_id):
        formats = []
        q = qualities(['Media', 'Alta', 'HQ', 'HD_READY', 'HD_FULL'])
        for manager in (self._manager, 'rtveplayw'):
            png = self._download_webpage(
                f'http://www.rtve.es/ztnr/movil/thumbnail/{manager}/videos/{video_id}.png',
                video_id, 'Downloading url information', query={'q': 'v2'})

            for quality, video_url in self._decrypt_url(png):
                ext = determine_ext(video_url)
                if ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        video_url, video_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls', fatal=False))
                elif ext == 'mpd':
                    formats.extend(self._extract_mpd_formats(
                        video_url, video_id, 'dash', fatal=False))
                else:
                    formats.append({
                        'format_id': quality,
                        'quality': q(quality),
                        'url': video_url,
                    })
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._download_json(
            f'http://www.rtve.es/api/videos/{video_id}/config/alacarta_videos.json',
            video_id)['page']['items'][0]
        if info['state'] == 'DESPU':
            raise ExtractorError('The video is no longer available', expected=True)
        title = info['title'].strip()
        formats = self._extract_png_formats(video_id)

        sbt_file = f'https://api2.rtve.es/api/videos/{video_id}/subtitulos.json'
        subtitles = self.extract_subtitles(video_id, sbt_file)

        is_live = info.get('live') is True

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': info.get('image'),
            'subtitles': subtitles,
            'duration': float_or_none(info.get('duration'), 1000),
            'is_live': is_live,
            'series': info.get('programTitle'),
        }

    def _get_subtitles(self, video_id, sub_file):
        subs = self._download_json(
            sub_file, video_id,
            'Downloading subtitles info')['page']['items']
        return dict(
            (s['lang'], [{'ext': 'vtt', 'url': s['src']}])
            for s in subs)


class RTVEAudioIE(RTVEALaCartaIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'rtve.es:audio'
    IE_DESC = 'RTVE audio'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/(alacarta|play)/audios/[^/]+/[^/]+/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'https://www.rtve.es/alacarta/audios/a-hombros-de-gigantes/palabra-ingeniero-codigos-informaticos-27-04-21/5889192/',
        'md5': 'ae06d27bff945c4e87a50f89f6ce48ce',
        'info_dict': {
            'id': '5889192',
            'ext': 'mp3',
            'title': 'Códigos informáticos',
            'duration': 349.440,
            'series': 'A hombros de gigantes',
        },
    }, {
        'url': 'https://www.rtve.es/play/audios/en-radio-3/ignatius-farray/5791165/',
        'md5': '072855ab89a9450e0ba314c717fa5ebc',
        'info_dict': {
            'id': '5791165',
            'ext': 'mp3',
            'title': 'Ignatius Farray',
            'thumbnail': r're:https?://.+/1613243011863.jpg',
            'duration': 3559.559,
            'series': 'En Radio 3',
        },
    }, {
        'url': 'https://www.rtve.es/play/audios/frankenstein-o-el-moderno-prometeo/capitulo-26-ultimo-muerte-victor-juan-jose-plans-mary-shelley/6082623/',
        'md5': '0eadab248cc8dd193fa5765712e84d5c',
        'info_dict': {
            'id': '6082623',
            'ext': 'mp3',
            'title': 'Capítulo 26 y último: La muerte de Victor',
            'thumbnail': r're:https?://.+/1632147445707.jpg',
            'duration': 3174.086,
            'series': 'Frankenstein o el moderno Prometeo',
        },
    }]

    def _extract_png_formats(self, audio_id):
        """
        This function retrieves media related png thumbnail which obfuscate
        valuable information about the media. This information is decrypted
        via base class _decrypt_url function providing media quality and
        media url
        """
        png = self._download_webpage(
            f'http://www.rtve.es/ztnr/movil/thumbnail/{self._manager}/audios/{audio_id}.png',
            audio_id, 'Downloading url information', query={'q': 'v2'})
        q = qualities(['Media', 'Alta', 'HQ', 'HD_READY', 'HD_FULL'])
        formats = []
        for quality, audio_url in self._decrypt_url(png):
            ext = determine_ext(audio_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    audio_url, audio_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    audio_url, audio_id, 'dash', fatal=False))
            else:
                formats.append({
                    'format_id': quality,
                    'quality': q(quality),
                    'url': audio_url,
                })
        return formats

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        info = self._download_json(
            f'https://www.rtve.es/api/audios/{audio_id}.json',
            audio_id)['page']['items'][0]

        return {
            'id': audio_id,
            'title': info['title'].strip(),
            'thumbnail': info.get('thumbnail'),
            'duration': float_or_none(info.get('duration'), 1000),
            'series': try_get(info, lambda x: x['programInfo']['title']),
            'formats': self._extract_png_formats(audio_id),
        }


class RTVEInfantilIE(RTVEALaCartaIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'rtve.es:infantil'
    IE_DESC = 'RTVE infantil'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/infantil/serie/[^/]+/video/[^/]+/(?P<id>[0-9]+)/'

    _TESTS = [{
        'url': 'https://www.rtve.es/infantil/serie/agus-lui-churros-crafts/video/gusano/7048976/',
        'md5': '7da8391b203a2d9cb665f11fae025e72',
        'info_dict': {
            'id': '7048976',
            'ext': 'mp4',
            'title': 'Gusano',
            'thumbnail': r're:https://img2\.rtve\.es/v/.*\.png',
            'duration': 292.86,
            'series': 'Agus & Lui: Churros y Crafts',
        },
        'expected_warnings': ['Failed to download MPD manifest', 'Failed to download m3u8 information'],
    }]


class RTVELiveIE(RTVEALaCartaIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'rtve.es:live'
    IE_DESC = 'RTVE.es live streams'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/directo/(?P<id>[a-zA-Z0-9-]+)'

    _TESTS = [{
        'url': 'http://www.rtve.es/directo/la-1/',
        'info_dict': {
            'id': 'la-1',
            'ext': 'mp4',
            'title': str,
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'live stream',
        },
        'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)
        title = self._html_extract_title(webpage)

        data_setup = self._search_regex(
            r'<div[^>]+class="[^"]*videoPlayer[^"]*"[^>]*data-setup=\'([^\']*)\'',
            webpage, 'data_setup',
        )
        data_setup = self._parse_json(data_setup, video_id)

        return {
            'id': video_id,
            'title': title,
            'formats': self._extract_png_formats(data_setup.get('idAsset')),
            'is_live': True,
        }


class RTVETelevisionIE(InfoExtractor):
    IE_NAME = 'rtve.es:television'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/television/[^/]+/[^/]+/(?P<id>\d+).shtml'

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
