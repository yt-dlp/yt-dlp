# coding: utf-8
from __future__ import unicode_literals

import base64
import re
import time

from .common import InfoExtractor
from ..compat import (
    compat_b64decode,
    compat_struct_unpack,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    remove_end,
    remove_start,
    sanitized_Request,
    std_headers,
)


def _decrypt_url(png):
    encrypted_data = compat_b64decode(png)
    text_index = encrypted_data.find(b'tEXt')
    text_chunk = encrypted_data[text_index - 4:]
    length = compat_struct_unpack('!I', text_chunk[:4])[0]
    # Use bytearray to get integers when iterating in both python 2.x and 3.x
    data = bytearray(text_chunk[8:8 + length])
    data = [chr(b) for b in data if b != 0]
    hash_index = data.index('#')
    alphabet_data = data[:hash_index]
    url_data = data[hash_index + 1:]
    if url_data[0] == 'H' and url_data[3] == '%':
        # remove useless HQ%% at the start
        url_data = url_data[4:]

    alphabet = []
    e = 0
    d = 0
    for l in alphabet_data:
        if d == 0:
            alphabet.append(l)
            d = e = (e + 1) % 4
        else:
            d -= 1
    url = ''
    f = 0
    e = 3
    b = 1
    for letter in url_data:
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


class RTVEALaCartaIE(InfoExtractor):
    IE_NAME = 'rtve.es:alacarta'
    IE_DESC = 'RTVE a la carta'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/(m/)?(alacarta/videos|filmoteca)/[^/]+/[^/]+/(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.rtve.es/alacarta/videos/balonmano/o-swiss-cup-masculina-final-espana-suecia/2491869/',
        'md5': '1d49b7e1ca7a7502c56a4bf1b60f1b43',
        'info_dict': {
            'id': '2491869',
            'ext': 'mp4',
            'title': 'Balonmano - Swiss Cup masculina. Final: España-Suecia',
            'duration': 5024.566,
        },
    }, {
        'note': 'Live stream',
        'url': 'http://www.rtve.es/alacarta/videos/television/24h-live/1694255/',
        'info_dict': {
            'id': '1694255',
            'ext': 'flv',
            'title': 'TODO',
        },
        'skip': 'The f4m manifest can\'t be used yet',
    }, {
        'url': 'http://www.rtve.es/alacarta/videos/servir-y-proteger/servir-proteger-capitulo-104/4236788/',
        'md5': 'e55e162379ad587e9640eda4f7353c0f',
        'info_dict': {
            'id': '4236788',
            'ext': 'mp4',
            'title': 'Servir y proteger - Capítulo 104 ',
            'duration': 3222.0,
        },
        'params': {
            'skip_download': True,  # requires ffmpeg
        },
    }, {
        'url': 'http://www.rtve.es/m/alacarta/videos/cuentame-como-paso/cuentame-como-paso-t16-ultimo-minuto-nuestra-vida-capitulo-276/2969138/?media=tve',
        'only_matching': True,
    }, {
        'url': 'http://www.rtve.es/filmoteca/no-do/not-1-introduccion-primer-noticiario-espanol/1465256/',
        'only_matching': True,
    }]

    def _real_initialize(self):
        user_agent_b64 = base64.b64encode(std_headers['User-Agent'].encode('utf-8')).decode('utf-8')
        manager_info = self._download_json(
            'http://www.rtve.es/odin/loki/' + user_agent_b64,
            None, 'Fetching manager info')
        self._manager = manager_info['manager']

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        info = self._download_json(
            'http://www.rtve.es/api/videos/%s/config/alacarta_videos.json' % video_id,
            video_id)['page']['items'][0]
        if info['state'] == 'DESPU':
            raise ExtractorError('The video is no longer available', expected=True)
        title = info['title']
        png_url = 'http://www.rtve.es/ztnr/movil/thumbnail/%s/videos/%s.png' % (self._manager, video_id)
        png_request = sanitized_Request(png_url)
        png_request.add_header('Referer', url)
        png = self._download_webpage(png_request, video_id, 'Downloading url information')
        video_url = _decrypt_url(png)
        ext = determine_ext(video_url)

        formats = []
        if not video_url.endswith('.f4m') and ext != 'm3u8':
            if '?' not in video_url:
                video_url = video_url.replace('resources/', 'auth/resources/')
            video_url = video_url.replace('.net.rtve', '.multimedia.cdn.rtve')

        if ext == 'm3u8':
            formats.extend(self._extract_m3u8_formats(
                video_url, video_id, ext='mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False))
        elif ext == 'f4m':
            formats.extend(self._extract_f4m_formats(
                video_url, video_id, f4m_id='hds', fatal=False))
        else:
            formats.append({
                'url': video_url,
            })
        self._sort_formats(formats)

        subtitles = None
        if info.get('sbtFile') is not None:
            subtitles = self.extract_subtitles(video_id, info['sbtFile'])

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': info.get('image'),
            'page_url': url,
            'subtitles': subtitles,
            'duration': float_or_none(info.get('duration'), scale=1000),
        }

    def _get_subtitles(self, video_id, sub_file):
        subs = self._download_json(
            sub_file + '.json', video_id,
            'Downloading subtitles info')['page']['items']
        return dict(
            (s['lang'], [{'ext': 'vtt', 'url': s['src']}])
            for s in subs)


class RTVEInfantilIE(InfoExtractor):
    IE_NAME = 'rtve.es:infantil'
    IE_DESC = 'RTVE infantil'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/infantil/serie/(?P<show>[^/]*)/video/(?P<short_title>[^/]*)/(?P<id>[0-9]+)/'

    _TESTS = [{
        'url': 'http://www.rtve.es/infantil/serie/cleo/video/maneras-vivir/3040283/',
        'md5': '915319587b33720b8e0357caaa6617e6',
        'info_dict': {
            'id': '3040283',
            'ext': 'mp4',
            'title': 'Maneras de vivir',
            'thumbnail': 'http://www.rtve.es/resources/jpg/6/5/1426182947956.JPG',
            'duration': 357.958,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._download_json(
            'http://www.rtve.es/api/videos/%s/config/alacarta_videos.json' % video_id,
            video_id)['page']['items'][0]

        webpage = self._download_webpage(url, video_id)
        vidplayer_id = self._search_regex(
            r' id="vidplayer([0-9]+)"', webpage, 'internal video ID')

        png_url = 'http://www.rtve.es/ztnr/movil/thumbnail/default/videos/%s.png' % vidplayer_id
        png = self._download_webpage(png_url, video_id, 'Downloading url information')
        video_url = _decrypt_url(png)

        return {
            'id': video_id,
            'ext': 'mp4',
            'title': info['title'],
            'url': video_url,
            'thumbnail': info.get('image'),
            'duration': float_or_none(info.get('duration'), scale=1000),
        }


class RTVELiveIE(InfoExtractor):
    IE_NAME = 'rtve.es:live'
    IE_DESC = 'RTVE.es live streams'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/directo/(?P<id>[a-zA-Z0-9-]+)'

    _TESTS = [{
        'url': 'http://www.rtve.es/directo/la-1/',
        'info_dict': {
            'id': 'la-1',
            'ext': 'mp4',
            'title': 're:^La 1 [0-9]{4}-[0-9]{2}-[0-9]{2}Z[0-9]{6}$',
        },
        'params': {
            'skip_download': 'live stream',
        }
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        start_time = time.gmtime()
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)
        title = remove_end(self._og_search_title(webpage), ' en directo en RTVE.es')
        title = remove_start(title, 'Estoy viendo ')
        title += ' ' + time.strftime('%Y-%m-%dZ%H%M%S', start_time)

        vidplayer_id = self._search_regex(
            (r'playerId=player([0-9]+)',
             r'class=["\'].*?\blive_mod\b.*?["\'][^>]+data-assetid=["\'](\d+)',
             r'data-id=["\'](\d+)'),
            webpage, 'internal video ID')
        png_url = 'http://www.rtve.es/ztnr/movil/thumbnail/amonet/videos/%s.png' % vidplayer_id
        png = self._download_webpage(png_url, video_id, 'Downloading url information')
        m3u8_url = _decrypt_url(png)
        formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'is_live': True,
        }


class RTVETelevisionIE(InfoExtractor):
    IE_NAME = 'rtve.es:television'
    _VALID_URL = r'https?://(?:www\.)?rtve\.es/television/[^/]+/[^/]+/(?P<id>\d+).shtml'

    _TEST = {
        'url': 'http://www.rtve.es/television/20160628/revolucion-del-movil/1364141.shtml',
        'info_dict': {
            'id': '3069778',
            'ext': 'mp4',
            'title': 'Documentos TV - La revolución del móvil',
            'duration': 3496.948,
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        alacarta_url = self._search_regex(
            r'data-location="alacarta_videos"[^<]+url&quot;:&quot;(http://www\.rtve\.es/alacarta.+?)&',
            webpage, 'alacarta url', default=None)
        if alacarta_url is None:
            raise ExtractorError(
                'The webpage doesn\'t contain any video', expected=True)

        return self.url_result(alacarta_url, ie=RTVEALaCartaIE.ie_key())
