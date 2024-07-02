import base64
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    RegexNotFoundError,
    determine_ext,
    join_nonempty,
    js_to_json,
)


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:(?:www\.)?rtp\.pt/play/(?P<subarea>.*/)?p(?P<program_id>[0-9]+)/)|(?:arquivos\.rtp\.pt/conteudos/))(?P<id>[^/?#]+)/?'
    _TESTS = [{
        'url': 'https://www.rtp.pt/play/p9165/e562949/por-do-sol',
        'info_dict': {
            'id': 'e562949',
            'ext': 'mp4',
            'title': 'Pôr do Sol Episódio 1',
            'description': 'Madalena Bourbon de Linhaça vive atormentada pelo segredo que esconde desde 1990. Matilde Bourbon de Linhaça sonha fugir com o seu amor proibido. O',
            'thumbnail': r're:^https?://.*\.(jpg|png)'
        },
    }, {
        'url': 'https://www.rtp.pt/play/p12646/e738493/telejornal',
        'info_dict': {
            'id': 'e738493',
            'ext': 'mp4',
            'title': 'Telejornal de 01 jan 2024 PARTE 1',
            'description': 'A mais rigorosa seleção de notícias, todos os dias às 20h00. De segunda a domingo, João Adelino Faria, José Rodrigues dos Santos e Ana Lourenço',
            'thumbnail': r're:^https?://.*\.(jpg|png)'
        },
    }, {
        'url': 'https://www.rtp.pt/play/p6646/e457262/grande-entrevista',
        'info_dict': {
            'id': 'e457262',
            'ext': 'mp4',
            'title': 'Grande Entrevista Episódio 7 - de 19 fev 2020',
            'description': 'Bruno Nogueira - É um dos mais originais humoristas portugueses e de maior êxito! Bruno Nogueira na Grande Entrevista com Vítor Gonçalves.',
            'thumbnail': r're:^https?://.*\.(jpg|png)'
        },
    }, {
        'url': 'https://www.rtp.pt/play/p8064/e750623/fronteira',
        'info_dict': {
            'id': 'e750623',
            'ext': 'mp4',
            'title': 'Fronteira de 26 fev 2024',
            'description': '1970. À aldeia de Fronteira chega um novo chefe de posto da Guarda Fiscal. Com convicções inabaláveis sobre a aplicação da Lei, rapidamente entr',
            'thumbnail': r're:^https?://.*\.(jpg|png)'
        },
    }, {
        'url': 'https://www.rtp.pt/play/estudoemcasa/p7776/e539826/portugues-1-ano',
        'info_dict': {
            'id': 'e539826',
            'ext': 'mp4',
            'title': 'Português - 1.º ano , aula 45 - 27 abr 2021 - Estudo Em Casa - RTP',
            'description': 'A História do Pedrito Coelho, de Beatrix Potter. O dígrafo \'lh\' - A História do Pedrito Coelho, de Beatrix Potter. O dígrafo \'lh\'.',
            'thumbnail': r're:^https?://.*\.(jpg|png)'
        },
    }, {
        'url': 'https://www.rtp.pt/play/zigzag/p11099/e747372/coelhos-corajosos',
        'info_dict': {
            'id': 'e747372',
            'ext': 'mp4',
            'title': 'Coelhos Corajosos Episódio 1 - de 12 fev 2024 - Zig Zag Play - RTP',
            'description': 'Boo e o seu irmão mais velho, Bop, vivem grandes aventuras com os seus amigos, e com os seus quatro irmãos pequeninos. Juntos e com muita coragem, e',
            'thumbnail': r're:^https?://.*\.(jpg|png)'
        },
    }, {
        'url': 'https://arquivos.rtp.pt/conteudos/liga-dos-ultimos-152/',
        'info_dict': {
            'id': 'liga-dos-ultimos-152',
            'ext': 'mp4',
            'title': 'Liga dos Últimos – RTP Arquivos',
            'description': 'Magazine desportivo, com apresentação de Álvaro Costa e comentários em estúdio do professor Hernâni Gonçalves e do sociólogo João Nuno Coelho. Destaque para os jogos de futebol das equipas dos escalões secundários de Portugal, com momentos dos jogos: Agrário de Lamas vs Pampilhoense e Apúlia vs Fragoso.',
            'thumbnail': r're:^https?://.*\.(jpg|png)'
        },
    }, {
        'url': 'https://www.rtp.pt/play/p510/aleixo-fm',
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

        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title', default='')

        # Raise error if episode is unavailable
        if 'Este episódio não se encontra disponível' in title:
            raise ExtractorError('Episode unavailable', expected=True)

        # Replace irrelevant string in title
        title = re.sub(r' -  ?RTP Play - RTP', '', title)

        # Check if it's a program split in parts
        part = self._html_search_regex(r'section\-parts.*<span.*>(.+?)</span>.*</ul>', webpage, 'part', default=None)

        # Add program part identification to title if it exists
        title = join_nonempty(title, part, delim=' ')

        try:
            # Extract f and config from page
            f, config = self._search_regex(
                r'''(?sx)
                    var\s+f\s*=\s*(?P<f>".*?"|{[^;]+?});\s*
                    var\s+player1\s+=\s+new\s+RTPPlayer\s*\((?P<config>{(?:(?!\*/).)+?})\);(?!\s*\*/)
                ''', webpage,
                'player config', group=('f', 'config'))

            f = self._parse_json(
                f, video_id,
                lambda data: self.__unobfuscate(data, video_id=video_id))

            config = self._parse_json(
                config, video_id,
                lambda data: self.__unobfuscate(data, video_id=video_id))

            config['file'] = f
        except RegexNotFoundError:
            # Estudo em Casa / Zig Zag / RTP Arquivos pages don't include f
            config = self._search_regex(
                r'''(?sx)
                    var\s+player1\s+=\s+new\s+RTPPlayer\s*\((?P<config>{(?:(?!\*/).)+?})\);(?!\s*\*/)
                ''', webpage,
                'just player config')

            config = self._parse_json(
                config, video_id,
                lambda data: self.__unobfuscate(data, video_id=video_id))

        formats = []
        file = config.get('file')
        if isinstance(file, dict):
            file_hls = file.get('hls')
            file_fps = file.get('fps')

            if file_hls is None and file_fps is not None:
                file_hls = file_fps.replace('drm-fps', 'hls')

            formats.extend(self._extract_m3u8_formats(
                file_hls, video_id, 'mp4', 'm3u8_native', m3u8_id='hls'))
        else:
            ext = determine_ext(file)

            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    file, video_id, 'mp4', 'm3u8_native', m3u8_id='hls'))

            else:
                formats.append({
                    'format_id': 'f',
                    'url': file,
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
