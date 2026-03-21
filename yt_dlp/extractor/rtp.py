import base64
import json
import re
import urllib.parse

from .common import InfoExtractor, Request
from ..utils import (
    determine_ext,
    int_or_none,
    join_nonempty,
    js_to_json,
    make_archive_id,
    parse_duration,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtp\.pt/play/(?:[^/#?]+/)?p(?P<program_id>\d+)/(?P<id>e\d+)(?:/[^/#?]+/(?P<asset_id>\d+))?'
    _TESTS = [{
        'url': 'http://www.rtp.pt/play/p405/e174042/paixoes-cruzadas',
        'md5': 'e736ce0c665e459ddb818546220b4ef8',
        'info_dict': {
            'id': '395769',
            'ext': 'mp3',
            'title': 'Paixões Cruzadas',
            'description': 'md5:af979e58ba0ab73f78435fc943fdb070',
            'thumbnail': r're:^https?://.*\.jpg',
            'series': 'Paixões Cruzadas',
            'duration': 2950.0,
            'modified_timestamp': 1553693464,
            'modified_date': '20190327',
            'timestamp': 1417219200,
            'upload_date': '20141129',
            'episode_id': 'e174042',
            'display_id': 'e174042-395769',
            '_old_archive_ids': ['rtp e174042'],
        },
    }, {
        'url': 'https://www.rtp.pt/play/zigzag/p13166/e757904/25-curiosidades-25-de-abril',
        'md5': '5b4859940e3adef61247a77dfb76046a',
        'info_dict': {
            'id': '1226642',
            'ext': 'mp4',
            'title': 'Estudar ou não estudar',
            'description': 'md5:3bfd7eb8bebfd5711a08df69c9c14c35',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1711958401,
            'duration': 146.0,
            'upload_date': '20240401',
            'modified_timestamp': 1712242991,
            'series': '25 Curiosidades, 25 de Abril',
            'episode_number': 2,
            'episode': 'Estudar ou não estudar',
            'modified_date': '20240404',
            'episode_id': 'e757904',
            'display_id': 'e757904-1226642',
            '_old_archive_ids': ['rtp e757904'],
        },
    }, {
        # Episode not accessible through API
        'url': 'https://www.rtp.pt/play/estudoemcasa/p7776/e500050/portugues-1-ano',
        'md5': '57660c0b46db9f22118c52cbd65975e4',
        'info_dict': {
            'id': '871639',
            'ext': 'mp4',
            'title': 'Português - 1.º ano',
            'duration': 1669.0,
            'description': 'md5:be68925c81269f8c6886589f25fe83ea',
            'upload_date': '20201020',
            'timestamp': 1603180799,
            'thumbnail': 'https://cdn-images.rtp.pt/EPG/imagens/39482_59449_64850.png?v=3&w=860',
            'episode_id': 'e500050',
            'display_id': 'e500050-871639',
            '_old_archive_ids': ['rtp e500050'],
        },
    }, {
        # 1st segment of a multi-segment episode
        'url': 'https://www.rtp.pt/play/p14335/e877072/a-nossa-tarde',
        'md5': '2aa3c89c95e852d6f04168b95d0d0632',
        'info_dict': {
            'id': '1364711',
            'ext': 'mp4',
            'display_id': 'e877072-1364711',
            'title': 'A Nossa Tarde',
            'duration': 1292.0,
            'thumbnail': r're:https://cdn-images\.rtp\.pt/multimedia/screenshots/p14335/p14335_1_20250922155118e161t0312\.jpg',
            'series': 'A Nossa Tarde',
            'season': '2025',
            'episode_id': 'e877072',
            'timestamp': 1758560188,
            'upload_date': '20250922',
            'modified_timestamp': 1758563110,
            'modified_date': '20250922',
            '_old_archive_ids': ['rtp e877072'],
        },
    }, {
        # 2nd segment of a multi-segment episode
        'url': 'https://www.rtp.pt/play/p14335/e877072/a-nossa-tarde/1364744',
        'md5': 'b624767af558a557372a6fcd1dcdfa17',
        'info_dict': {
            'id': '1364744',
            'ext': 'mp4',
            'display_id': 'e877072-1364744',
            'title': 'A Nossa Tarde',
            'duration': 3270.0,
            'thumbnail': r're:https://cdn-images\.rtp\.pt/multimedia/screenshots/p14335/p14335_2_20250922165718e161t0412\.jpg',
            'series': 'A Nossa Tarde',
            'season': '2025',
            'episode_id': 'e877072',
            'timestamp': 1758560188,
            'upload_date': '20250922',
            'modified_timestamp': 1758563110,
            'modified_date': '20250922',
        },
    }]

    _USER_AGENT = 'rtpplay/2.0.66 (pt.rtp.rtpplay; build:2066; iOS 15.8.3) Alamofire/5.9.1'
    _AUTH_TOKEN = None

    def _fetch_auth_token(self):
        if self._AUTH_TOKEN:
            return self._AUTH_TOKEN
        self._AUTH_TOKEN = traverse_obj(self._download_json(Request(
            'https://rtpplayapi.rtp.pt/play/api/2/token-manager',
            headers={
                'Accept': '*/*',
                'rtp-play-auth': 'RTPPLAY_MOBILE_IOS',
                'rtp-play-auth-hash': 'fac9c328b2f27e26e03d7f8942d66c05b3e59371e16c2a079f5c83cc801bd3ee',
                'rtp-play-auth-timestamp': '2145973229682',
                'User-Agent': self._USER_AGENT,
            }, extensions={'keep_header_casing': True}), None,
            note='Fetching guest auth token', errnote='Could not fetch guest auth token',
            fatal=False), ('token', 'token', {str}))
        return self._AUTH_TOKEN

    @staticmethod
    def _cleanup_media_url(url):
        if urllib.parse.urlparse(url).netloc == 'streaming-ondemand.rtp.pt':
            return None
        return url.replace('/drm-fps/', '/hls/').replace('/drm-dash/', '/dash/')

    def _extract_formats(self, media_urls, display_id):
        formats = []
        subtitles = {}
        for media_url in set(traverse_obj(media_urls, (..., {url_or_none}, {self._cleanup_media_url}))):
            ext = determine_ext(media_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    media_url, display_id, m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    media_url, display_id, mpd_id='dash', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': media_url,
                    'format_id': 'http',
                })
        return formats, subtitles

    def _extract_from_api(self, program_id, episode_id, asset_id):
        display_id = join_nonempty(episode_id, asset_id)
        auth_token = self._fetch_auth_token()
        if not auth_token:
            return None

        episode_data = traverse_obj(self._download_json(
            f'https://www.rtp.pt/play/api/1/get-episode/{program_id}/{episode_id[1:]}',
            display_id, query={'include_assets': 'true', 'include_webparams': 'true'},
            headers={
                'Accept': '*/*',
                'Authorization': f'Bearer {auth_token}',
                'User-Agent': self._USER_AGENT,
            }, fatal=False), 'result', {dict})
        if not episode_data:
            return None

        if not asset_id:
            asset_data = traverse_obj(episode_data, ('assets', 0, {dict}))
            asset_id = traverse_obj(asset_data, ('asset_id', {str}))
            if not asset_id:
                return None
            display_id = join_nonempty(episode_id, asset_id)
            old_archive_ids = [make_archive_id(self, episode_id)]
        else:
            asset_data = traverse_obj(episode_data, ('assets', lambda _, v: v['asset_id'] == asset_id, any))
            old_archive_ids = None

        if not asset_data:
            return None

        asset_urls = traverse_obj(asset_data, ('asset_url', {dict}))
        media_urls = traverse_obj(asset_urls, (
            ((('hls', 'dash'), 'stream_url'), ('multibitrate', ('url_hls', 'url_dash'))),))
        formats, subtitles = self._extract_formats(media_urls, display_id)

        for sub_data in traverse_obj(asset_urls, ('subtitles', 'vtt_list', lambda _, v: url_or_none(v['file']))):
            subtitles.setdefault(sub_data.get('code') or 'pt', []).append({
                'url': sub_data['file'],
                'name': sub_data.get('language'),
            })

        return {
            'id': asset_id,
            'display_id': display_id,
            'episode_id': episode_id,
            '_old_archive_ids': old_archive_ids,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(asset_data, {
                'thumbnail': ('asset_thumbnail', {url_or_none}),
                'duration': ('asset_duration', {parse_duration}),
            }),
            **traverse_obj(episode_data, ('episode', {
                'title': (('episode_title', 'program_title'), {str}, filter, any),
                'alt_title': ('episode_subtitle', {str}, filter),
                'description': (('episode_description', 'episode_summary'), {str}, filter, any),
                'timestamp': ('episode_air_date', {parse_iso8601(delimiter=' ')}),
                'modified_timestamp': ('episode_lastchanged', {parse_iso8601(delimiter=' ')}),
                'episode': ('episode_title', {str}, filter),
                'episode_number': ('episode_number', {int_or_none}),
                'season': ('program_season', {str}, filter),
                'series': ('program_title', {str}, filter),
            })),
        }

    _RX_OBFUSCATION = re.compile(r'''(?xs)
        atob\s*\(\s*decodeURIComponent\s*\(\s*
            (\[[0-9A-Za-z%,'"]*\])
        \s*\.\s*join\(\s*(?:""|'')\s*\)\s*\)\s*\)
    ''')

    def __unobfuscate(self, data):
        return self._RX_OBFUSCATION.sub(
            lambda m: json.dumps(
                base64.b64decode(urllib.parse.unquote(
                    ''.join(json.loads(m.group(1))),
                )).decode('iso-8859-1')),
            data)

    def _extract_from_html(self, url, episode_id, asset_id):
        display_id = join_nonempty(episode_id, asset_id)
        webpage = self._download_webpage(url, display_id)
        if not asset_id:
            asset_id = self._search_regex(r'\basset_id\s*:\s*"(\d+)"', webpage, 'asset ID')
            display_id = join_nonempty(episode_id, asset_id)
            old_archive_ids = [make_archive_id(self, episode_id)]
        else:
            old_archive_ids = None

        formats = []
        subtitles = {}
        media_urls = traverse_obj(re.findall(r'(?:var\s+f\s*=|RTPPlayer\({[^}]+file:)\s*({[^}]+}|"[^"]+")', webpage), (
            -1, (({self.__unobfuscate}, {js_to_json}, {json.loads}, {dict.values}, ...), {json.loads})))
        formats, subtitles = self._extract_formats(media_urls, display_id)

        return {
            'id': asset_id,
            'display_id': display_id,
            'episode_id': episode_id,
            'formats': formats,
            'subtitles': subtitles,
            'description': self._html_search_meta(['og:description', 'twitter:description'], webpage, default=None),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage, default=None),
            **self._search_json_ld(webpage, display_id, default={}),
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage, default=None),
            '_old_archive_ids': old_archive_ids,
        }

    def _real_extract(self, url):
        program_id, episode_id, asset_id = self._match_valid_url(url).group('program_id', 'id', 'asset_id')
        return self._extract_from_api(program_id, episode_id, asset_id) or self._extract_from_html(url, episode_id, asset_id)
