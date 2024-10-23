import base64
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    join_nonempty,
    js_to_json,
)


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?rtp\.pt/play/(?P<subarea>.*/)?p(?P<program_id>\d+)/|arquivos\.rtp\.pt/conteudos/)(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.rtp.pt/play/p9165/e562949/por-do-sol',
        'info_dict': {
            'id': 'e562949',
            'ext': 'mp4',
            'title': 'Pôr do Sol Episódio 1',
            'description': 'Madalena Bourbon de Linhaça vive atormentada pelo segredo que esconde desde 1990. Matilde Bourbon de Linhaça sonha fugir com o seu amor proibido. O',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.rtp.pt/play/p12646/e738493/telejornal',
        'info_dict': {
            'id': 'e738493',
            'ext': 'mp4',
            'title': 'Telejornal de 01 jan 2024 PARTE 1',
            'description': 'A mais rigorosa seleção de notícias, todos os dias às 20h00. De segunda a domingo, João Adelino Faria, José Rodrigues dos Santos e Ana Lourenço',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.rtp.pt/play/p6646/e457262/grande-entrevista',
        'info_dict': {
            'id': 'e457262',
            'ext': 'mp4',
            'title': 'Grande Entrevista Episódio 7 - de 19 fev 2020',
            'description': 'Bruno Nogueira - É um dos mais originais humoristas portugueses e de maior êxito! Bruno Nogueira na Grande Entrevista com Vítor Gonçalves.',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.rtp.pt/play/p1525/e738522/a-mosca',
        'info_dict': {
            'id': 'e738522',
            'ext': 'mp4',
            'title': 'A Mosca de 02 jan 2024',
            'description': 'Ano novo, vida nova - Ano novo, vida nova',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.rtp.pt/play/estudoemcasa/p7776/e539826/portugues-1-ano',
        'info_dict': {
            'id': 'e539826',
            'ext': 'mp4',
            'title': 'Português - 1.º ano , aula 45 - 27 abr 2021',
            'description': 'A História do Pedrito Coelho, de Beatrix Potter. O dígrafo \'lh\' - A História do Pedrito Coelho, de Beatrix Potter. O dígrafo \'lh\'.',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.rtp.pt/play/zigzag/p13857/e794575/zig-zag-zzz-e-amigos',
        'info_dict': {
            'id': 'e794575',
            'ext': 'mp4',
            'title': 'Zig, Zag, Zzz e Amigos Episódio 1 - de 16 set 2024',
            'description': 'O Brinquedo Perdido - Zig, Zag e Zzz são três amigos inseparáveis que partilham aventuras emocionantes e cheias de imaginação. Exploram o mundo �',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.rtp.pt/play/palco/p13151/premio-miguel-rovisco-2023-requiem-por-isabel',
        'info_dict': {
            'id': 'premio-miguel-rovisco-2023-requiem-por-isabel',
            'ext': 'mp4',
            'title': 'Prémio Miguel Rovisco 23: Requiem Por Isabel de 30 mar 2024',
            'description': 'Lucrécia foi a atriz mais famosa e requisitada do seu tempo. Este já não é o seu tempo. A debater-se com a decrepitude física e financeira, foi o',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://arquivos.rtp.pt/conteudos/liga-dos-ultimos-152/',
        'info_dict': {
            'id': 'liga-dos-ultimos-152',
            'ext': 'mp4',
            'title': 'Liga dos Últimos – RTP Arquivos',
            'description': 'Magazine desportivo, com apresentação de Álvaro Costa e comentários em estúdio do professor Hernâni Gonçalves e do sociólogo João Nuno Coelho. Destaque para os jogos de futebol das equipas dos escalões secundários de Portugal, com momentos dos jogos: Agrário de Lamas vs Pampilhoense e Apúlia vs Fragoso.',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
    }, {
        'url': 'https://www.rtp.pt/play/p510/e786608/aleixo-fm',
        'info_dict': {
            'id': 'e786608',
            'ext': 'mp3',
            'title': 'Aleixo FM de 31 jul 2024',
            'description': 'Melhor dia pra casar - Já o diz Joaquim de Magalhães Fernandes Barreiros, comummente conhecido como Quim Barreiros. Mas será mesmo este o melhor di',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
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

        # Title tag includes relevant data
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title', default='')

        # Raise error if episode is unavailable
        if 'Este episódio não se encontra disponível' in title:
            raise ExtractorError('Episode unavailable', expected=True)

        # Replace irrelevant text in title
        title = re.sub(r' -  ?(RTP Play|Estudo Em Casa|Zig Zag Play|RTP Palco)( - RTP)?', '', title)

        # Check if it's a episode split in parts
        part = self._html_search_regex(r'section\-parts.*<span.*>(.+?)</span>.*</ul>', webpage, 'part', default=None)

        # Add episode part identification to title if it exists
        title = join_nonempty(title, part, delim=' ')

        # Extract f and config from page
        f, config = self._search_regex(
            r'''(?sx)
                (?:var\s+f\s*=\s*(?P<f>".*?"|{[^;]+?});\s*)?
                var\s+player1?\s+=\s+new\s+RTPPlayer\s*\((?P<config>{(?:(?!\*/).)+?})\);(?!\s*\*/)
            ''', webpage,
            'player config', group=('f', 'config'))

        config = self._parse_json(
            config, video_id,
            lambda data: self.__unobfuscate(data, video_id=video_id))

        # Estudo em Casa / Zig Zag / Palco / RTP Arquivos subareas don't include f
        f = config['file'] if not f else self._parse_json(
            f, video_id,
            lambda data: self.__unobfuscate(data, video_id=video_id))

        formats = []
        if isinstance(f, dict):
            file_hls = f.get('hls')
            file_fps = f.get('fps')

            if file_fps is not None:
                # RTP Arquivos specific use case
                if '/arquivo/' in file_fps:
                    file_key = config['fileKey']
                    split_file_key = file_key.split('/')
                    filename = split_file_key[-1]
                    del split_file_key[-1]
                    split_file_key.extend([f'index.m3u8?tlm=hls&streams={filename}.m3u8'])

                    path = '/'.join(split_file_key)

                    file_hls = f'https://streaming-arquivo-ondemand.rtp.pt/nas2.share{path}'
                elif file_hls is None:
                    file_hls = file_fps.replace('drm-fps', 'hls')

            formats.extend(self._extract_m3u8_formats(
                file_hls, video_id, 'mp4', 'm3u8_native', m3u8_id='hls'))
        else:
            ext = determine_ext(f)

            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    f, video_id, 'mp4', 'm3u8_native', m3u8_id='hls'))

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
            'description': self._html_search_meta(['og:description', 'description'], webpage),
            'thumbnail': config.get('poster') or self._og_search_thumbnail(webpage),
            'subtitles': subtitles,
        }
