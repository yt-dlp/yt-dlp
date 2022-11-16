import re

from .common import InfoExtractor


class MediaStreamIE(InfoExtractor):
    _VALID_URL = r'https?://mdstrm.com/(?:embed|live-stream)/(?P<id>\w+)'

    _TESTS = [{
        'url': 'https://mdstrm.com/embed/6318e3f1d1d316083ae48831',
        'md5': '97b4f2634b8e8612cc574dfcd504df05',
        'info_dict': {
            'id': '6318e3f1d1d316083ae48831',
            'title': 'Video: Así fue el despido de Thomas Tuchel del Chelsea',
            'description': 'md5:358ce1e1396010d50a1ece1be3633c95',
            'thumbnail': r're:^https?://[^?#]+6318e3f1d1d316083ae48831',
            'ext': 'mp4',
        },
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://www.multimedios.com/video/costa-rica-tv-en-vivo/v2616',
        'info_dict': {
            'id': '5a7b1e63a8da282c34d65445',
            'title': 're:mmtv-costarica',
            'description': 'mmtv-costarica',
            'thumbnail': 're:^https?://[^?#]+5a7b1e63a8da282c34d65445',
            'ext': 'mp4',
            'live_status': "is_live",
        },
        'params': {
            'skip_download': 'Livestream'
        },
    }, {
        'url': 'https://www.multimedios.com/television/clases-de-llaves-y-castigos-quien-sabe-mas',
        'md5': 'de31f0b1ecc321fb35bf22d58734ea40',
        'info_dict': {
            'id': '63731bab8ec9b308a2c9ed28',
            'title': 'Clases de llaves y castigos ¿Quién sabe más?',
            'description': 'md5:1b49aa1ee5a4b32fbd66104b2d629e9d',
            'thumbnail': 're:^https?://[^?#]+63731bab8ec9b308a2c9ed28',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.americatv.com.pe/videos/esto-es-guerra/facundo-gonzalez-sufrio-fuerte-golpe-durante-competencia-frente-hugo-garcia-eeg-noticia-139120',
        'info_dict': {
            'id': '63756df1c638b008a5659dec',
            'title': 'Facundo González sufrió fuerte golpe durante competencia frente a Hugo García en EEG',
            'description': 'md5:9490c034264afd756eef7b2c3adee69e',
            'thumbnail': 're:^https?://[^?#]+63756df1c638b008a5659dec',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.americatv.com.pe/videos/al-fondo-hay-sitio/nuevas-lomas-town-bernardo-mata-se-enfrento-sujeto-luchar-amor-macarena-noticia-139083',
        'info_dict': {
            'id': '637307669609130f74cd3a6e',
            'title': 'Las Nuevas Lomas Town: Bernardo De La Mata se enfrentó a sujeto para luchar por el amor de Macarena',
            'description': 'md5:60d71772f1e1496923539ae58aa17124',
            'thumbnail': 're:^https?://[^?#]+637307669609130f74cd3a6e',
            'ext': 'mp4',
        },
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for mobj in re.finditer(r'<script[^>]+>[^>]*playerMdStream.mdstreamVideo\(\s*[\'"](?P<video_id>\w+)', webpage):
            yield f'https://mdstrm.com/embed/{mobj.group("video_id")}'

        for mobj in re.finditer(r'<iframe[^>]src\s*=\s*"https://mdstrm.com/(?P<video_type>[\w-]+)/(?P<video_id>\w+)',
                                webpage):
            yield f'https://mdstrm.com/{mobj.group("video_type")}/{mobj.group("video_id")}'

        for mobj in re.finditer(
            r'''(?x)
                <(?:div|ps-mediastream)[^>]+
                class\s*=\s*"[^"]*MediaStreamVideoPlayer[^"]*"[^>]+
                data-video-id\s*=\s*"(?P<video_id>\w+)\s*"
                (?:\s*data-video-type\s*=\s*"(?P<video_type>[^"]+))?
                ''', webpage):

            video_type = 'embed'
            if mobj.group('video_type') == 'live':
                video_type = 'live-stream'

            yield f'https://mdstrm.com/{video_type}/{mobj.group("video_id")}'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if 'Debido a tu ubicación no puedes ver el contenido' in webpage:
            self.raise_geo_restricted()

        player_config = self._search_json(r'window.MDSTRM.OPTIONS\s*=', webpage, 'metadata', video_id)

        formats, subtitles = [], {}
        for video_format in player_config['src']:
            if video_format == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(player_config['src'][video_format], video_id)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif video_format == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(player_config['src'][video_format], video_id)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': player_config['src'][video_format],
                })

        return {
            'id': video_id,
            'title': self._og_search_title(webpage) or player_config.get('title'),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': player_config.get('type') == 'live',
            'thumbnail': self._og_search_thumbnail(webpage),
        }
