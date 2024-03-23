from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    urlencode_postdata,
)


class AtresPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?atresplayer\.com/[^/]+/[^/]+/[^/]+(?:/[^/]+)?/(?P<display_id>.+?)_(?P<id>[0-9a-f]{24})'
    _NETRC_MACHINE = 'atresplayer'
    _TESTS = [
        {
            'url': 'https://www.atresplayer.com/antena3/series/pequenas-coincidencias/temporada-1/capitulo-7-asuntos-pendientes_5d4aa2c57ed1a88fc715a615/',
            'info_dict': {
                'id': '5d4aa2c57ed1a88fc715a615',
                'ext': 'mp4',
                'title': 'Capítulo 7: Asuntos pendientes',
                'description': 'md5:7634cdcb4d50d5381bedf93efb537fbc',
                'duration': 3413,
            },
            'skip': 'This video is only available for registered users'
        },
        {
            'url': 'https://www.atresplayer.com/lasexta/programas/el-club-de-la-comedia/temporada-4/capitulo-10-especial-solidario-nochebuena_5ad08edf986b2855ed47adc4/',
            'only_matching': True,
        },
        {
            'url': 'https://www.atresplayer.com/antena3/series/el-secreto-de-puente-viejo/el-chico-de-los-tres-lunares/capitulo-977-29-12-14_5ad51046986b2886722ccdea/',
            'only_matching': True,
        },
    ]

    def _handle_error(self, e, code):
        if isinstance(e.cause, HTTPError) and e.cause.status == code:
            error = self._parse_json(e.cause.response.read(), None)
            if error.get('error') == 'required_registered':
                self.raise_login_required()
            if error.get('error') == 'invalid_request':
                raise ExtractorError('Authentication failed', expected=True)
            raise ExtractorError(error['error_description'], expected=True)
        raise

    def _perform_login(self, username, password):
        try:
            self._download_webpage(
                'https://account.atresplayer.com/auth/v1/login', None,
                'Logging in', headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }, data=urlencode_postdata({
                    'username': username,
                    'password': password,
                }))
        except ExtractorError as e:
            self._handle_error(e, 400)

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()

        page = self._download_webpage(url, video_id, 'Downloading video page')
        preloaded_state_regex = r'window\.__PRELOADED_STATE__\s*=\s*(\{(.*?)\});'
        preloaded_state_text = self._html_search_regex(preloaded_state_regex, page, 'preloaded state')
        preloaded_state = self._parse_json(preloaded_state_text, video_id)
        link_info = next(iter(preloaded_state['links'].values()))

        try:
            metadata = self._download_json(link_info['href'], video_id)
        except ExtractorError as e:
            self._handle_error(e, 403)

        try:
            episode = self._download_json(metadata['urlVideo'], video_id)
        except ExtractorError as e:
            self._handle_error(e, 403)

        title = episode['titulo']

        formats = []
        subtitles = {}
        for source in episode.get('sources', []):
            src = source.get('src')
            if not src:
                continue
            src_type = source.get('type')
            if src_type == 'application/vnd.apple.mpegurl':
                new_formats, new_subtitles = self._extract_m3u8_formats_and_subtitles(
                    src, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False)
            elif src_type == 'application/dash+xml':
                new_formats, new_subtitles = self._extract_mpd_formats_and_subtitles(
                    src, video_id, mpd_id='dash', fatal=False)
            if new_formats:
                formats.extend(new_formats)
            if new_subtitles:
                subtitles = self._merge_subtitles(subtitles, new_subtitles)

        heartbeat = episode.get('heartbeat') or {}
        omniture = episode.get('omniture') or {}
        get_meta = lambda x: heartbeat.get(x) or omniture.get(x)

        return {
            'display_id': display_id,
            'id': video_id,
            'title': title,
            'description': episode.get('descripcion'),
            'thumbnail': episode.get('imgPoster'),
            'duration': int_or_none(episode.get('duration')),
            'formats': formats,
            'channel': get_meta('channel'),
            'season': get_meta('season'),
            'episode_number': int_or_none(get_meta('episodeNumber')),
            'subtitles': subtitles,
        }
