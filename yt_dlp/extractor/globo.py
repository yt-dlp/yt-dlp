# coding: utf-8
from __future__ import unicode_literals

import base64
import hashlib
import json
import random
import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    orderedSet,
    str_or_none,
)


class GloboIE(InfoExtractor):
    _VALID_URL = r'(?:globo:|https?://.+?\.globo\.com/(?:[^/]+/)*(?:v/(?:[^/]+/)?|videos/))(?P<id>\d{7,})'
    _NETRC_MACHINE = 'globo'
    _TESTS = [{
        'url': 'http://g1.globo.com/carros/autoesporte/videos/t/exclusivos-do-g1/v/mercedes-benz-gla-passa-por-teste-de-colisao-na-europa/3607726/',
        'md5': 'b3ccc801f75cd04a914d51dadb83a78d',
        'info_dict': {
            'id': '3607726',
            'ext': 'mp4',
            'title': 'Mercedes-Benz GLA passa por teste de colisão na Europa',
            'duration': 103.204,
            'uploader': 'Globo.com',
            'uploader_id': '265',
        },
    }, {
        'url': 'http://globoplay.globo.com/v/4581987/',
        'md5': 'f36a1ecd6a50da1577eee6dd17f67eff',
        'info_dict': {
            'id': '4581987',
            'ext': 'mp4',
            'title': 'Acidentes de trânsito estão entre as maiores causas de queda de energia em SP',
            'duration': 137.973,
            'uploader': 'Rede Globo',
            'uploader_id': '196',
        },
    }, {
        'url': 'http://canalbrasil.globo.com/programas/sangue-latino/videos/3928201.html',
        'only_matching': True,
    }, {
        'url': 'http://globosatplay.globo.com/globonews/v/4472924/',
        'only_matching': True,
    }, {
        'url': 'http://globotv.globo.com/t/programa/v/clipe-sexo-e-as-negas-adeus/3836166/',
        'only_matching': True,
    }, {
        'url': 'http://globotv.globo.com/canal-brasil/sangue-latino/t/todos-os-videos/v/ator-e-diretor-argentino-ricado-darin-fala-sobre-utopias-e-suas-perdas/3928201/',
        'only_matching': True,
    }, {
        'url': 'http://canaloff.globo.com/programas/desejar-profundo/videos/4518560.html',
        'only_matching': True,
    }, {
        'url': 'globo:3607726',
        'only_matching': True,
    }]

    def _real_initialize(self):
        email, password = self._get_login_info()
        if email is None:
            return

        try:
            glb_id = (self._download_json(
                'https://login.globo.com/api/authentication', None, data=json.dumps({
                    'payload': {
                        'email': email,
                        'password': password,
                        'serviceId': 4654,
                    },
                }).encode(), headers={
                    'Content-Type': 'application/json; charset=utf-8',
                }) or {}).get('glbId')
            if glb_id:
                self._set_cookie('.globo.com', 'GLBID', glb_id)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                resp = self._parse_json(e.cause.read(), None)
                raise ExtractorError(resp.get('userMessage') or resp['id'], expected=True)
            raise

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'http://api.globovideos.com/videos/%s/playlist' % video_id,
            video_id)['videos'][0]
        if not self._downloader.params.get('allow_unplayable_formats') and video.get('encrypted') is True:
            raise ExtractorError('This video is DRM protected.', expected=True)

        title = video['title']

        formats = []
        subtitles = {}
        for resource in video['resources']:
            resource_id = resource.get('_id')
            resource_url = resource.get('url')
            resource_type = resource.get('type')
            if not resource_url or (resource_type == 'media' and not resource_id) or resource_type not in ('subtitle', 'media'):
                continue

            if resource_type == 'subtitle':
                subtitles.setdefault(resource.get('language') or 'por', []).append({
                    'url': resource_url,
                })
                continue

            security = self._download_json(
                'http://security.video.globo.com/videos/%s/hash' % video_id,
                video_id, 'Downloading security hash for %s' % resource_id, query={
                    'player': 'desktop',
                    'version': '5.19.1',
                    'resource_id': resource_id,
                })

            security_hash = security.get('hash')
            if not security_hash:
                message = security.get('message')
                if message:
                    raise ExtractorError(
                        '%s returned error: %s' % (self.IE_NAME, message), expected=True)
                continue

            hash_code = security_hash[:2]
            padding = '%010d' % random.randint(1, 10000000000)
            if hash_code in ('04', '14'):
                received_time = security_hash[3:13]
                received_md5 = security_hash[24:]
                hash_prefix = security_hash[:23]
            elif hash_code in ('02', '12', '03', '13'):
                received_time = security_hash[2:12]
                received_md5 = security_hash[22:]
                padding += '1'
                hash_prefix = '05' + security_hash[:22]

            padded_sign_time = compat_str(int(received_time) + 86400) + padding
            md5_data = (received_md5 + padded_sign_time + '0xAC10FD').encode()
            signed_md5 = base64.urlsafe_b64encode(hashlib.md5(md5_data).digest()).decode().strip('=')
            signed_hash = hash_prefix + padded_sign_time + signed_md5
            signed_url = '%s?h=%s&k=html5&a=%s&u=%s' % (resource_url, signed_hash, 'F' if video.get('subscriber_only') else 'A', security.get('user') or '')

            if resource_id.endswith('m3u8') or resource_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(
                    signed_url, resource_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            elif resource_id.endswith('mpd') or resource_url.endswith('.mpd'):
                formats.extend(self._extract_mpd_formats(
                    signed_url, resource_id, mpd_id='dash', fatal=False))
            elif resource_id.endswith('manifest') or resource_url.endswith('/manifest'):
                formats.extend(self._extract_ism_formats(
                    signed_url, resource_id, ism_id='mss', fatal=False))
            else:
                formats.append({
                    'url': signed_url,
                    'format_id': 'http-%s' % resource_id,
                    'height': int_or_none(resource.get('height')),
                })

        self._sort_formats(formats)

        duration = float_or_none(video.get('duration'), 1000)
        uploader = video.get('channel')
        uploader_id = str_or_none(video.get('channel_id'))

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'formats': formats,
            'subtitles': subtitles,
        }


class GloboArticleIE(InfoExtractor):
    _VALID_URL = r'https?://.+?\.globo\.com/(?:[^/]+/)*(?P<id>[^/.]+)(?:\.html)?'

    _VIDEOID_REGEXES = [
        r'\bdata-video-id=["\'](\d{7,})',
        r'\bdata-player-videosids=["\'](\d{7,})',
        r'\bvideosIDs\s*:\s*["\']?(\d{7,})',
        r'\bdata-id=["\'](\d{7,})',
        r'<div[^>]+\bid=["\'](\d{7,})',
    ]

    _TESTS = [{
        'url': 'http://g1.globo.com/jornal-nacional/noticia/2014/09/novidade-na-fiscalizacao-de-bagagem-pela-receita-provoca-discussoes.html',
        'info_dict': {
            'id': 'novidade-na-fiscalizacao-de-bagagem-pela-receita-provoca-discussoes',
            'title': 'Novidade na fiscalização de bagagem pela Receita provoca discussões',
            'description': 'md5:c3c4b4d4c30c32fce460040b1ac46b12',
        },
        'playlist_count': 1,
    }, {
        'url': 'http://g1.globo.com/pr/parana/noticia/2016/09/mpf-denuncia-lula-marisa-e-mais-seis-na-operacao-lava-jato.html',
        'info_dict': {
            'id': 'mpf-denuncia-lula-marisa-e-mais-seis-na-operacao-lava-jato',
            'title': "Lula era o 'comandante máximo' do esquema da Lava Jato, diz MPF",
            'description': 'md5:8aa7cc8beda4dc71cc8553e00b77c54c',
        },
        'playlist_count': 6,
    }, {
        'url': 'http://gq.globo.com/Prazeres/Poder/noticia/2015/10/all-o-desafio-assista-ao-segundo-capitulo-da-serie.html',
        'only_matching': True,
    }, {
        'url': 'http://gshow.globo.com/programas/tv-xuxa/O-Programa/noticia/2014/01/xuxa-e-junno-namoram-muuuito-em-luau-de-zeze-di-camargo-e-luciano.html',
        'only_matching': True,
    }, {
        'url': 'http://oglobo.globo.com/rio/a-amizade-entre-um-entregador-de-farmacia-um-piano-19946271',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if GloboIE.suitable(url) else super(GloboArticleIE, cls).suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_ids = []
        for video_regex in self._VIDEOID_REGEXES:
            video_ids.extend(re.findall(video_regex, webpage))
        entries = [
            self.url_result('globo:%s' % video_id, GloboIE.ie_key())
            for video_id in orderedSet(video_ids)]
        title = self._og_search_title(webpage, fatal=False)
        description = self._html_search_meta('description', webpage)
        return self.playlist_result(entries, display_id, title, description)
