import json
import re

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    orderedSet,
    str_or_none,
)
from ..utils.traversal import subs_list_to_dict, traverse_obj


class GloboIE(InfoExtractor):
    _VALID_URL = r'(?:globo:|https?://.+?\.globo\.com/(?:[^/]+/))(?P<id>\d{7,})'
    _NETRC_MACHINE = 'globo'
    _VIDEO_VIEW = '''
    query getVideoView($videoId: ID!) {
        video(id: $videoId) {
            duration
            description
            headline
            title {
                originProgramId
                headline
            }
        }
    }
    '''
    _TESTS = [{
        'url': 'https://globoplay.globo.com/v/3607726/',
        'info_dict': {
            'id': '3607726',
            'ext': 'mp4',
            'title': 'Mercedes-Benz GLA passa por teste de colisão na Europa',
            'duration': 103.204,
            'uploader': 'G1 ao vivo',
            'uploader_id': '4209',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://globoplay.globo.com/v/4581987/',
        'info_dict': {
            'id': '4581987',
            'ext': 'mp4',
            'title': 'Acidentes de trânsito estão entre as maiores causas de queda de energia em SP',
            'duration': 137.973,
            'uploader': 'Bom Dia Brasil',
            'uploader_id': '810',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'globo:3607726',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = self._download_json(
            'https://cloud-jarvis.globo.com/graphql', video_id,
            query={
                'operationName': 'getVideoView',
                'variables': f'{{"videoId":{video_id}}}',
                'query': self._VIDEO_VIEW,
            }, headers={
                'content-type': 'application/json',
                'x-platform-id': 'web',
                'x-device-id': 'desktop',
                'x-client-version': '2024.12-5',
            })['data']['video']

        formats = []
        video = self._download_json(
            'https://playback.video.globo.com/v4/video-session', video_id,
            f'Downloading resource info for {video_id}',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'player_type': 'desktop',
                'video_id': video_id,
                'quality': 'max',
                'content_protection': 'widevine',
                'vsid': '2938bc7c-9376-d4b7-ee91-ce46dbbf9f4d',
                'tz': '-03:00',
                'version': 1,
            }).encode())

        if traverse_obj(video, ('resource', 'drm_protection_enabled', {bool})):
            self.report_drm(video_id)

        main_source = video['sources'][0]

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            main_source['url'], video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)
        self._merge_subtitles(traverse_obj(main_source, ('text', ..., {
            'url': ('subtitle', 'srt', 'url', {str_or_none}),
        }, all, {subs_list_to_dict(lang='por')})), target=subtitles)

        return {
            'id': video_id,
            **traverse_obj(info, {
                'title': ('headline', {str}),
                'duration': ('duration', {float_or_none(scale=1000)}),
                'uploader': ('title', 'headline', {str}),
                'uploader_id': ('title', 'originProgramId', {str_or_none}),
            }),
            'formats': formats,
            'subtitles': subtitles,
        }


class GloboArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?!globoplay).+?\.globo\.com/(?:[^/]+/)*(?P<id>[^/.]+)(?:\.html)?'

    _VIDEOID_REGEXES = [
        r'\bdata-video-id=["\'](\d{7,})["\']',
        r'\bdata-player-videosids=["\'](\d{7,})["\']',
        r'\bvideosIDs\s*:\s*["\']?(\d{7,})',
        r'\bdata-id=["\'](\d{7,})["\']',
        r'<div[^>]+\bid=["\'](\d{7,})["\']',
        r'<bs-player[^>]+\bvideoid=["\'](\d{8,})["\']',
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
    }, {
        'url': 'https://ge.globo.com/video/ta-na-area-como-foi-assistir-ao-jogo-do-palmeiras-que-a-globo-nao-passou-10287094.ghtml',
        'info_dict': {
            'id': 'ta-na-area-como-foi-assistir-ao-jogo-do-palmeiras-que-a-globo-nao-passou-10287094',
            'title': 'Tá na Área: como foi assistir ao jogo do Palmeiras que a Globo não passou',
            'description': 'md5:2d089d036c4c9675117d3a56f8c61739',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://redeglobo.globo.com/rpc/meuparana/noticia/a-producao-de-chocolates-no-parana.ghtml',
        'info_dict': {
            'id': 'a-producao-de-chocolates-no-parana',
            'title': 'A produção de chocolates no Paraná',
            'description': 'md5:f2e3daf00ffd1dc0e9a8a6c7cfb0a89e',
        },
        'playlist_count': 2,
    }]

    @classmethod
    def suitable(cls, url):
        return False if GloboIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_ids = []
        for video_regex in self._VIDEOID_REGEXES:
            video_ids.extend(re.findall(video_regex, webpage))
        entries = [
            self.url_result(f'globo:{video_id}', GloboIE.ie_key())
            for video_id in orderedSet(video_ids)]
        title = self._og_search_title(webpage).strip()
        description = self._html_search_meta('description', webpage)
        return self.playlist_result(entries, display_id, title, description)
