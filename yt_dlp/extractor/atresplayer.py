import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class AtresPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?atresplayer\.com/(?:[^/?#]+/){4}(?P<display_id>.+?)_(?P<id>[0-9a-f]{24})'
    _NETRC_MACHINE = 'atresplayer'
    _TESTS = [{
        'url': 'https://www.atresplayer.com/lasexta/programas/el-objetivo/clips/mbappe-describe-como-entrenador-a-carlo-ancelotti-sabe-cuando-tiene-que-ser-padre-jefe-amigo-entrenador_67f2dfb2fb6ab0e4c7203849/',
        'info_dict': {
            'ext': 'mp4',
            'id': '67f2dfb2fb6ab0e4c7203849',
            'display_id': 'md5:c203f8d4e425ed115ba56a1c6e4b3e6c',
            'title': 'Mbappé describe como entrenador a Carlo Ancelotti: "Sabe cuándo tiene que ser padre, jefe, amigo, entrenador..."',
            'channel': 'laSexta',
            'duration': 31,
            'thumbnail': 'https://imagenes.atresplayer.com/atp/clipping/cmsimages02/2025/04/06/B02DBE1E-D59B-4683-8404-1A9595D15269/1920x1080.jpg',
            'tags': ['Entrevista informativa', 'Actualidad', 'Debate informativo', 'Política', 'Economía', 'Sociedad', 'Cara a cara', 'Análisis', 'Más periodismo'],
            'series': 'El Objetivo',
            'season': 'Temporada 12',
            'timestamp': 1743970079,
            'upload_date': '20250406',
        },
    }, {
        'url': 'https://www.atresplayer.com/antena3/programas/el-hormiguero/clips/revive-la-entrevista-completa-a-miguel-bose-en-el-hormiguero_67f836baa4a5b0e4147ca59a/',
        'info_dict': {
            'ext': 'mp4',
            'id': '67f836baa4a5b0e4147ca59a',
            'display_id': 'revive-la-entrevista-completa-a-miguel-bose-en-el-hormiguero',
            'title': 'Revive la entrevista completa a Miguel Bosé en El Hormiguero',
            'description': 'md5:c6d2b591408d45a7bc2986dfb938eb72',
            'channel': 'Antena 3',
            'duration': 2556,
            'thumbnail': 'https://imagenes.atresplayer.com/atp/clipping/cmsimages02/2025/04/10/9076395F-F1FD-48BE-9F18-540DBA10EBAD/1920x1080.jpg',
            'tags': ['Entrevista', 'Variedades', 'Humor', 'Entretenimiento', 'Te sigo', 'Buen rollo', 'Cara a cara'],
            'series': 'El Hormiguero ',
            'season': 'Temporada 14',
            'timestamp': 1744320111,
            'upload_date': '20250410',
        },
    }, {
        'url': 'https://www.atresplayer.com/flooxer/series/biara-proyecto-lazarus/temporada-1/capitulo-3-supervivientes_67a6038b64ceca00070f4f69/',
        'info_dict': {
            'ext': 'mp4',
            'id': '67a6038b64ceca00070f4f69',
            'display_id': 'capitulo-3-supervivientes',
            'title': 'Capítulo 3: Supervivientes',
            'description': 'md5:65b231f20302f776c2b0dd24594599a1',
            'channel': 'Flooxer',
            'duration': 1196,
            'thumbnail': 'https://imagenes.atresplayer.com/atp/clipping/cmsimages01/2025/02/14/17CF90D3-FE67-40C5-A941-7825B3E13992/1920x1080.jpg',
            'tags': ['Juvenil', 'Terror', 'Piel de gallina', 'Te sigo', 'Un break', 'Del tirón'],
            'series': 'BIARA: Proyecto Lázarus',
            'season': 'Temporada 1',
            'season_number': 1,
            'episode': 'Episode 3',
            'episode_number': 3,
            'timestamp': 1743095191,
            'upload_date': '20250327',
        },
    }, {
        'url': 'https://www.atresplayer.com/lasexta/programas/el-club-de-la-comedia/temporada-4/capitulo-10-especial-solidario-nochebuena_5ad08edf986b2855ed47adc4/',
        'only_matching': True,
    }, {
        'url': 'https://www.atresplayer.com/antena3/series/el-secreto-de-puente-viejo/el-chico-de-los-tres-lunares/capitulo-977-29-12-14_5ad51046986b2886722ccdea/',
        'only_matching': True,
    }]
    _API_BASE = 'https://api.atresplayer.com/'

    def _perform_login(self, username, password):
        try:
            self._download_webpage(
                'https://account.atresplayer.com/auth/v1/login', None,
                'Logging in', 'Failed to log in', data=urlencode_postdata({
                    'username': username,
                    'password': password,
                }))
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise ExtractorError('Invalid username and/or password', expected=True)
            raise

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()

        metadata_url = self._download_json(
            self._API_BASE + 'client/v1/url', video_id, 'Downloading API endpoint data',
            query={'href': urllib.parse.urlparse(url).path})['href']
        metadata = self._download_json(metadata_url, video_id)

        try:
            video_data = self._download_json(metadata['urlVideo'], video_id, 'Downloading video data')
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                error = self._parse_json(e.cause.response.read(), None)
                if error.get('error') == 'required_registered':
                    self.raise_login_required()
                raise ExtractorError(error['error_description'], expected=True)
            raise

        formats = []
        subtitles = {}
        for source in traverse_obj(video_data, ('sources', lambda _, v: url_or_none(v['src']))):
            src_url = source['src']
            src_type = source.get('type')
            if src_type in ('application/vnd.apple.mpegurl', 'application/hls+legacy', 'application/hls+hevc'):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    src_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            elif src_type in ('application/dash+xml', 'application/dash+hevc'):
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    src_url, video_id, mpd_id='dash', fatal=False)
            else:
                continue
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'display_id': display_id,
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_data, {
                'title': ('titulo', {str}),
                'description': ('descripcion', {str}),
                'duration': ('duration', {int_or_none}),
                'thumbnail': ('imgPoster', {url_or_none}, {lambda v: f'{v}1920x1080.jpg'}),
                'age_limit': ('ageRating', {parse_age_limit}),
            }),
            **traverse_obj(metadata, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'duration': ('duration', {int_or_none}),
                'tags': ('tags', ..., 'title', {str}),
                'age_limit': ('ageRating', {parse_age_limit}),
                'series': ('format', 'title', {str}),
                'season': ('currentSeason', 'title', {str}),
                'season_number': ('currentSeason', 'seasonNumber', {int_or_none}),
                'episode_number': ('numberOfEpisode', {int_or_none}),
                'timestamp': ('publicationDate', {int_or_none(scale=1000)}),
                'channel': ('channel', 'title', {str}),
            }),
        }
