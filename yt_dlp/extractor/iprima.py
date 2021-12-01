# coding: utf-8
from __future__ import unicode_literals

import re
import time

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    js_to_json,
    urlencode_postdata,
    ExtractorError,
    parse_qs
)


class IPrimaIE(InfoExtractor):
    _VALID_URL = r'https?://(?!cnn)(?:[^/]+)\.iprima\.cz/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _GEO_BYPASS = False
    _NETRC_MACHINE = 'iprima'
    _LOGIN_URL = 'https://auth.iprima.cz/oauth2/login'
    _TOKEN_URL = 'https://auth.iprima.cz/oauth2/token'
    access_token = None

    _TESTS = [{
        'url': 'https://prima.iprima.cz/particka/92-epizoda',
        'info_dict': {
            'id': 'p51388',
            'ext': 'mp4',
            'title': 'Partička (92)',
            'description': 'md5:859d53beae4609e6dd7796413f1b6cac',
            'upload_date': '20201103',
            'timestamp': 1604437480,
        },
        'params': {
            'skip_download': True,  # m3u8 download
        },
    }, {
        'url': 'http://play.iprima.cz/particka/particka-92',
        'only_matching': True,
    }, {
        # geo restricted
        'url': 'http://play.iprima.cz/closer-nove-pripady/closer-nove-pripady-iv-1',
        'only_matching': True,
    }, {
        'url': 'https://prima.iprima.cz/my-little-pony/mapa-znameni-2-2',
        'only_matching': True,
    }, {
        'url': 'https://prima.iprima.cz/porady/jak-se-stavi-sen/rodina-rathousova-praha',
        'only_matching': True,
    }, {
        'url': 'http://www.iprima.cz/filmy/desne-rande',
        'only_matching': True,
    }, {
        'url': 'https://zoom.iprima.cz/10-nejvetsich-tajemstvi-zahad/posvatna-mista-a-stavby',
        'only_matching': True,
    }, {
        'url': 'https://krimi.iprima.cz/mraz-0/sebevrazdy',
        'only_matching': True,
    }, {
        'url': 'https://cool.iprima.cz/derava-silnice-nevadi',
        'only_matching': True,
    }, {
        'url': 'https://love.iprima.cz/laska-az-za-hrob/slib-dany-bratrovi',
        'only_matching': True,
    }]

    def _login(self):
        username, password = self._get_login_info()

        if username is None or password is None:
            self.raise_login_required('Login is required to access any iPrima content', method='password')

        login_page = self._download_webpage(
            self._LOGIN_URL, None, note='Downloading login page',
            errnote='Downloading login page failed')

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            '_email': username,
            '_password': password})

        _, login_handle = self._download_webpage_handle(
            self._LOGIN_URL, None, data=urlencode_postdata(login_form),
            note='Logging in')

        code = parse_qs(login_handle.geturl()).get('code')[0]
        if not code:
            raise ExtractorError('Login failed', expected=True)

        token_request_data = {
            'scope': 'openid+email+profile+phone+address+offline_access',
            'client_id': 'prima_sso',
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'https://auth.iprima.cz/sso/auth-check'}

        token_data = self._download_json(
            self._TOKEN_URL, None,
            note='Downloading token', errnote='Downloading token failed',
            data=urlencode_postdata(token_request_data))

        self.access_token = token_data.get('access_token')
        if self.access_token is None:
            raise ExtractorError('Getting token failed', expected=True)

    def _raise_access_error(self, error_code):
        if error_code == 'PLAY_GEOIP_DENIED':
            self.raise_geo_restricted(countries=['CZ'], metadata_available=True)
        elif error_code is not None:
            self.raise_no_formats('Access to stream infos forbidden', expected=True)

    def _real_initialize(self):
        if not self.access_token:
            self._login()

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = self._html_search_meta(
            ['og:title', 'twitter:title'],
            webpage, 'title', default=None)

        video_id = self._search_regex((
            r'productId\s*=\s*([\'"])(?P<id>p\d+)\1',
            r'pproduct_id\s*=\s*([\'"])(?P<id>p\d+)\1'),
            webpage, 'real id', group='id')

        metadata = self._download_json(
            f'https://api.play-backend.iprima.cz/api/v1//products/id-{video_id}/play',
            video_id, note='Getting manifest URLs', errnote='Failed to get manifest URLs',
            headers={'X-OTT-Access-Token': self.access_token},
            expected_status=403)

        self._raise_access_error(metadata.get('errorCode'))

        stream_infos = metadata.get('streamInfos')
        formats = []
        if stream_infos is None:
            self.raise_no_formats('Reading stream infos failed', expected=True)
        else:
            for manifest in stream_infos:
                manifest_type = manifest.get('type')
                manifest_url = manifest.get('url')
                ext = determine_ext(manifest_url)
                if manifest_type == 'HLS' or ext == 'm3u8':
                    formats += self._extract_m3u8_formats(
                        manifest_url, video_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id='hls', fatal=False)
                elif manifest_type == 'DASH' or ext == 'mpd':
                    formats += self._extract_mpd_formats(
                        manifest_url, video_id, mpd_id='dash', fatal=False)
            self._sort_formats(formats)

        final_result = self._search_json_ld(webpage, video_id) or {}
        final_result.update({
            'id': video_id,
            'title': title,
            'thumbnail': self._html_search_meta(
                ['thumbnail', 'og:image', 'twitter:image'],
                webpage, 'thumbnail', default=None),
            'formats': formats,
            'description': self._html_search_meta(
                ['description', 'og:description', 'twitter:description'],
                webpage, 'description', default=None)})

        return final_result


class IPrimaCNNIE(InfoExtractor):
    _VALID_URL = r'https?://cnn\.iprima\.cz/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _GEO_BYPASS = False

    _TESTS = [{
        'url': 'https://cnn.iprima.cz/porady/strunc/24072020-koronaviru-mam-plne-zuby-strasit-druhou-vlnou-je-absurdni-rika-senatorka-dernerova',
        'info_dict': {
            'id': 'p716177',
            'ext': 'mp4',
            'title': 'md5:277c6b1ed0577e51b40ddd35602ff43e',
        },
        'params': {
            'skip_download': 'm3u8'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._set_cookie('play.iprima.cz', 'ott_adult_confirmed', '1')

        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(
            webpage, default=None) or self._search_regex(
            r'<h1>([^<]+)', webpage, 'title')

        video_id = self._search_regex(
            (r'<iframe[^>]+\bsrc=["\'](?:https?:)?//(?:api\.play-backend\.iprima\.cz/prehravac/embedded|prima\.iprima\.cz/[^/]+/[^/]+)\?.*?\bid=(p\d+)',
             r'data-product="([^"]+)">',
             r'id=["\']player-(p\d+)"',
             r'playerId\s*:\s*["\']player-(p\d+)',
             r'\bvideos\s*=\s*["\'](p\d+)'),
            webpage, 'real id')

        playerpage = self._download_webpage(
            'http://play.iprima.cz/prehravac/init',
            video_id, note='Downloading player', query={
                '_infuse': 1,
                '_ts': round(time.time()),
                'productId': video_id,
            }, headers={'Referer': url})

        formats = []

        def extract_formats(format_url, format_key=None, lang=None):
            ext = determine_ext(format_url)
            new_formats = []
            if format_key == 'hls' or ext == 'm3u8':
                new_formats = self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False)
            elif format_key == 'dash' or ext == 'mpd':
                return
                new_formats = self._extract_mpd_formats(
                    format_url, video_id, mpd_id='dash', fatal=False)
            if lang:
                for f in new_formats:
                    if not f.get('language'):
                        f['language'] = lang
            formats.extend(new_formats)

        options = self._parse_json(
            self._search_regex(
                r'(?s)(?:TDIPlayerOptions|playerOptions)\s*=\s*({.+?});\s*\]\]',
                playerpage, 'player options', default='{}'),
            video_id, transform_source=js_to_json, fatal=False)
        if options:
            for key, tracks in options.get('tracks', {}).items():
                if not isinstance(tracks, list):
                    continue
                for track in tracks:
                    src = track.get('src')
                    if src:
                        extract_formats(src, key.lower(), track.get('lang'))

        if not formats:
            for _, src in re.findall(r'src["\']\s*:\s*(["\'])(.+?)\1', playerpage):
                extract_formats(src)

        if not formats and '>GEO_IP_NOT_ALLOWED<' in playerpage:
            self.raise_geo_restricted(countries=['CZ'], metadata_available=True)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': formats,
            'description': self._og_search_description(webpage, default=None),
        }
