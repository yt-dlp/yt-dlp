import base64
import itertools
import json
import re
import uuid

from .common import InfoExtractor
from ..utils import (
    clean_html,
    remove_end,
    js_to_json,
    traverse_obj,
    urljoin,
)


class MediaStreamBaseIE(InfoExtractor):
    _EMBED_BASE_URL = 'https://mdstrm.com/embed'
    _BASE_URL_RE = r'https?://mdstrm\.com/(?:embed|live-stream)'

    def _extract_mediastream_urls(self, webpage):
        yield from traverse_obj(list(self._yield_json_ld(webpage, None)), (
            lambda _, v: v['@type'] == 'VideoObject', ('embedUrl', 'contentUrl'),
            {lambda x: x if re.match(rf'{self._BASE_URL_RE}/\w+', x) else None}))

        for mobj in re.finditer(r'<script[^>]+>[^>]*playerMdStream\.mdstreamVideo\(\s*[\'"](?P<video_id>\w+)', webpage):
            yield f'{self._EMBED_BASE_URL}/{mobj.group("video_id")}'

        yield from re.findall(
            rf'<iframe[^>]+\bsrc="({self._BASE_URL_RE}/\w+)', webpage)

        for mobj in re.finditer(
            r'''(?x)
                <(?:div|ps-mediastream)[^>]+
                (class="[^"]*MediaStreamVideoPlayer)[^"]*"[^>]+
                data-video-id="(?P<video_id>\w+)"
                (?:\s*data-video-type="(?P<video_type>[^"]+))?
                (?:[^>]*>\s*<div[^>]+\1[^"]*"[^>]+data-mediastream=["\'][^>]+
                    https://mdstrm\.com/(?P<live>live-stream))?
                ''', webpage):

            video_type = 'live-stream' if mobj.group('video_type') == 'live' or mobj.group('live') else 'embed'
            yield f'https://mdstrm.com/{video_type}/{mobj.group("video_id")}'


class MediaStreamIE(MediaStreamBaseIE):
    _VALID_URL = MediaStreamBaseIE._BASE_URL_RE + r'/(?P<id>\w+)'

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
        'params': {'skip_download': 'm3u8'},
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://www.multimedios.com/video/costa-rica-tv-en-vivo/v2616',
        'info_dict': {
            'id': '5a7b1e63a8da282c34d65445',
            'title': 're:mmtv-costarica',
            'description': 'mmtv-costarica',
            'thumbnail': 're:^https?://[^?#]+5a7b1e63a8da282c34d65445',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'Livestream'},
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
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.americatv.com.pe/videos/esto-es-guerra/facundo-gonzalez-sufrio-fuerte-golpe-durante-competencia-frente-hugo-garcia-eeg-noticia-139120',
        'info_dict': {
            'id': '63756df1c638b008a5659dec',
            'title': 'Facundo González sufrió fuerte golpe durante competencia frente a Hugo García en EEG',
            'description': 'md5:9490c034264afd756eef7b2c3adee69e',
            'thumbnail': 're:^https?://[^?#]+63756df1c638b008a5659dec',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.americatv.com.pe/videos/al-fondo-hay-sitio/nuevas-lomas-town-bernardo-mata-se-enfrento-sujeto-luchar-amor-macarena-noticia-139083',
        'info_dict': {
            'id': '637307669609130f74cd3a6e',
            'title': 'Las Nuevas Lomas Town: Bernardo De La Mata se enfrentó a sujeto para luchar por el amor de Macarena',
            'description': 'md5:60d71772f1e1496923539ae58aa17124',
            'thumbnail': 're:^https?://[^?#]+637307669609130f74cd3a6e',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _extract_from_webpage(self, url, webpage):
        for embed_url in self._extract_mediastream_urls(webpage):
            yield self.url_result(embed_url, MediaStreamIE, None)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        for message in [
            'Debido a tu ubicación no puedes ver el contenido',
            'You are not allowed to watch this video: Geo Fencing Restriction'
        ]:
            if message in webpage:
                self.raise_geo_restricted()

        player_config = self._search_json(r'window\.MDSTRM\.OPTIONS\s*=', webpage, 'metadata', video_id)

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


class CaracolTvPlayIE(InfoExtractor):
    _VALID_URL = r'https?://play\.caracoltv\.com/videoDetails/(?P<id>[^/?]+)'
    _NETRC_MACHINE = 'caracoltv-play'

    _TESTS = [{
        'url': 'https://play.caracoltv.com/videoDetails/OTo4NGFmNjUwOWQ2ZmM0NTg2YWRiOWU0MGNhOWViOWJkYQ==',
        'info_dict': {
            'id': 'OTo4NGFmNjUwOWQ2ZmM0NTg2YWRiOWU0MGNhOWViOWJkYQ==',
            'title': 'La teoría del promedio',
            'description': 'md5:1cdd6d2c13f19ef0d9649ab81a023ac3',
        },
        'playlist_count': 6,
    }, {
        'url': 'https://play.caracoltv.com/videoDetails/OTo3OWM4ZTliYzQxMmM0MTMxYTk4Mjk2YjdjNGQ4NGRkOQ==/ella?season=0',
        'info_dict': {
            'id': 'OTo3OWM4ZTliYzQxMmM0MTMxYTk4Mjk2YjdjNGQ4NGRkOQ==',
            'title': 'Ella',
            'description': 'md5:a639b1feb5ddcc0cff92a489b4e544b8',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://play.caracoltv.com/videoDetails/OTpiYTY1YTVmOTI5MzI0ZWJhOGZiY2Y3MmRlOWZlYmJkOA==/la-vuelta-al-mundo-en-80-risas-2022?season=0',
        'info_dict': {
            'id': 'OTpiYTY1YTVmOTI5MzI0ZWJhOGZiY2Y3MmRlOWZlYmJkOA==',
            'title': 'La vuelta al mundo en 80 risas 2022',
            'description': 'md5:e97aac36106e5c37ebf947b3350106a4',
        },
        'playlist_count': 17,
    }]

    _USER_TOKEN = None

    def _extract_app_token(self, webpage):
        config_js_path = self._search_regex(
            r'<script[^>]+src\s*=\s*"([^"]+coreConfig.js[^"]+)', webpage, 'config_js_url', fatal=False)

        mediation_config = {} if not config_js_path else self._search_json(
            r'mediation\s*:', self._download_webpage(
                urljoin('https://play.caracoltv.com/', config_js_path), None, fatal=False),
            'mediation_config', None, transform_source=js_to_json, fatal=False)

        key = traverse_obj(
            mediation_config, ('live', 'key')) or '795cd9c089a1fc48094524a5eba85a3fca1331817c802f601735907c8bbb4f50'
        secret = traverse_obj(
            mediation_config, ('live', 'secret')) or '64dec00a6989ba83d087621465b5e5d38bdac22033b0613b659c442c78976fa0'

        return base64.b64encode(f'{key}:{secret}'.encode()).decode()

    def _login(self, email, password):
        webpage = self._download_webpage('https://play.caracoltv.com/', None, fatal=False)
        app_token = self._extract_app_token(webpage)

        bearer_token = self._download_json(
            'https://eu-gateway.inmobly.com/applications/oauth', None, data={}, headers={
                'Authorization': f'Basic {app_token}',
            })['token']

        self._USER_TOKEN = self._download_json(
            'https://eu-gateway.inmobly.com/user/login', None, headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer' + bearer_token
            }, data=json.dumps({
                'device_data': {
                    'device_id': str(uuid.uuid4()),
                    'device_token': '',
                    'device_type': 'web'
                },
                'login_data': {
                    'enabled': True,
                    'email': email,
                    'password': password,
                }
            }).encode())['user_token']

    def _perform_login(self, username, password):
        self._login(username, password)

    def _extract_series_season(self, series_id, season_id, season_number):
        api_response = self._download_json(
            'https://eu-gateway.inmobly.com/feed', series_id, query={'season_id': season_id},
            headers={'Authorization': 'Bearer ' + self._USER_TOKEN})

        for episode in api_response['items']:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(episode['stream_url'], series_id, 'mp4')

            yield {
                'id': episode['id'],
                'title': episode.get('name'),
                'description': episode.get('description'),
                'formats': formats,
                'subtitles': subtitles,
                'thumbnails': traverse_obj(
                    episode, ('extra_thumbs', ..., {'url': 'thumb_url', 'height': 'height', 'width': 'width'})),
                'series_id': series_id,
                'season_id': season_id,
                'season_number': season_number,
                'episode_number': episode.get('item_order'),
            }

    def _real_extract(self, url):
        series_id = self._match_id(url)

        if self._USER_TOKEN is None:
            self._login('guest@inmobly.com', 'Test@gus1')

        series_api_response = self._download_json(
            'https://eu-gateway.inmobly.com/feed', series_id, query={'include_ids': series_id},
            headers={'Authorization': 'Bearer ' + self._USER_TOKEN})['items'][0]

        return self.playlist_result(
            itertools.chain.from_iterable(
                self._extract_series_season(series_id, season['id'], season.get('order'))
                for season in series_api_response['seasons']),
            series_id, playlist_title=series_api_response.get('name'),
            playlist_description=series_api_response.get('description'))


class Canal1IE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^.]+\.)?canal1\.com\.co/(?:[^?&])+/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://canal1.com.co/noticias/napa-i-una-cadena-de-produccion-de-arroz-que-se-quedo-en-veremos-y-abandonada-en-el-departamento-del-choco/',
        'info_dict': {
            'id': '63b39f6b354977084b85ab54',
            'display_id': 'napa-i-una-cadena-de-produccion-de-arroz-que-se-quedo-en-veremos-y-abandonada-en-el-departamento-del-choco',
            'title': 'Ñapa I Una cadena de producción de arroz que se quedó en veremos y abandonada en el departamento del Chocó',
            'description': 'md5:bc49c6d64d20610ea1e7daf079a0d013',
            'thumbnail': r're:^https?://[^?#]+63b39f6b354977084b85ab54',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://noticias.canal1.com.co/noticias/tres-i-el-triste-record-que-impuso-elon-musk-el-dueno-de-tesla-y-de-twitter/',
        'info_dict': {
            'id': '63b39e93f5fd223aa32250fb',
            'display_id': 'tres-i-el-triste-record-que-impuso-elon-musk-el-dueno-de-tesla-y-de-twitter',
            'title': 'Tres I El triste récord que impuso Elon Musk, el dueño de Tesla y de Twitter',
            'description': 'md5:d9f691f131a21ce6767ca6c05d17d791',
            'thumbnail': r're:^https?://[^?#]+63b39e93f5fd223aa32250fb',
            'ext': 'mp4',
        },
    }, {
        # Geo-restricted to Colombia
        'url': 'https://canal1.com.co/programas/guerreros-canal-1/video-inedito-guerreros-despedida-kewin-zarate/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        url = self._search_regex(r'"embedUrl"\s*:\s*"([^"]+)', webpage, "embedUrl")

        return self.url_result(url, display_id=display_id, url_transparent=True)


class WinSportsVideoIE(MediaStreamBaseIE):
    _VALID_URL = r'https?://www\.winsports\.co/videos/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://www.winsports.co/videos/siempre-castellanos-gran-atajada-del-portero-cardenal-para-evitar-la-caida-de-su-arco-60536',
        'info_dict': {
            'id': '62dc8357162c4b0821fcfb3c',
            'display_id': 'siempre-castellanos-gran-atajada-del-portero-cardenal-para-evitar-la-caida-de-su-arco-60536',
            'title': '¡Siempre Castellanos! Gran atajada del portero \'cardenal\' para evitar la caída de su arco',
            'description': 'md5:eb811b2b2882bdc59431732c06b905f2',
            'thumbnail': r're:^https?://[^?#]+62dc8357162c4b0821fcfb3c',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.winsports.co/videos/observa-aqui-los-goles-del-empate-entre-tolima-y-nacional-60548',
        'info_dict': {
            'id': '62dcb875ef12a5526790b552',
            'display_id': 'observa-aqui-los-goles-del-empate-entre-tolima-y-nacional-60548',
            'title': 'Observa aquí los goles del empate entre Tolima y Nacional',
            'description': 'md5:b19402ba6e46558b93fd24b873eea9c9',
            'thumbnail': r're:^https?://[^?#]+62dcb875ef12a5526790b552',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.winsports.co/videos/equidad-vuelve-defender-su-arco-de-remates-de-junior',
        'info_dict': {
            'id': '63fa7eca72f1741ad3a4d515',
            'display_id': 'equidad-vuelve-defender-su-arco-de-remates-de-junior',
            'title': '⚽ Equidad vuelve a defender su arco de remates de Junior',
            'description': 'Remate de Sierra',
            'thumbnail': r're:^https?://[^?#]+63fa7eca72f1741ad3a4d515',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.winsports.co/videos/bucaramanga-se-quedo-con-el-grito-de-gol-en-la-garganta',
        'info_dict': {
            'id': '6402adb62bbf3b18d454e1b0',
            'display_id': 'bucaramanga-se-quedo-con-el-grito-de-gol-en-la-garganta',
            'title': '⚽Bucaramanga se quedó con el grito de gol en la garganta',
            'description': 'Gol anulado Bucaramanga',
            'thumbnail': r're:^https?://[^?#]+6402adb62bbf3b18d454e1b0',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        data = self._search_json(
            r'<script\s*[^>]+data-drupal-selector="drupal-settings-json">', webpage, 'data', display_id)

        mediastream_url = urljoin(f'{self._EMBED_BASE_URL}/', (
            traverse_obj(data, (
                (('settings', 'mediastream_formatter', ..., 'mediastream_id'), 'url'), {str}), get_all=False)
            or next(self._extract_mediastream_urls(webpage), None)))

        if not mediastream_url:
            self.raise_no_formats('No MediaStream embed found in webpage')

        title = clean_html(remove_end(
            self._search_json_ld(webpage, display_id, expected_type='VideoObject', default={}).get('title')
            or self._og_search_title(webpage), '| Win Sports'))

        return self.url_result(
            mediastream_url, MediaStreamIE, display_id, url_transparent=True, display_id=display_id, video_title=title)
