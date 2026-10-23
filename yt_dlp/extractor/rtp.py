import base64
import json
import re
import urllib.parse

from .common import InfoExtractor, Request
from ..utils import (
    determine_ext,
    int_or_none,
    js_to_json,
    make_archive_id,
    parse_duration,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtp\.pt/play/(?:[^/#?]+/)?(?P<program_id>p\d+)/(?P<episode_id>e\d+)(?:/[^/#?]+/(?P<asset_id>\d+))?'
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
            'series_id': 'p405',
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
            'series_id': 'p13166',
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
            'series_id': 'p7776',
            '_old_archive_ids': ['rtp e500050'],
        },
        'expected_warnings': ['Episode data not found in API response; falling back to web extraction'],
    }, {
        # Ambiguous URL for 1st part of a multi-part episode without --no-playlist
        'url': 'https://www.rtp.pt/play/p14335/e877072/a-nossa-tarde',
        'info_dict': {
            'id': 'e877072',
            'title': 'A Nossa Tarde',
            'duration': 6545.0,
            'series': 'A Nossa Tarde',
            'series_id': 'p14335',
            'season': '2025',
            'episode_id': 'e877072',
            'timestamp': 1758560188,
            'upload_date': '20250922',
            'modified_timestamp': 1758563110,
            'modified_date': '20250922',
        },
        'playlist_count': 3,
    }, {
        # Ambiguous URL for 1st part of a multi-part episode with --no-playlist
        'url': 'https://www.rtp.pt/play/p14335/e877072/a-nossa-tarde',
        'md5': '2aa3c89c95e852d6f04168b95d0d0632',
        'info_dict': {
            'id': '1364711',
            'ext': 'mp4',
            'title': 'A Nossa Tarde',
            'duration': 1292.0,
            'thumbnail': r're:https://cdn-images\.rtp\.pt/multimedia/screenshots/p14335/p14335_1_20250922155118e161t0312\.jpg',
            'series': 'A Nossa Tarde',
            'series_id': 'p14335',
            'season': '2025',
            'episode_id': 'e877072',
            'timestamp': 1758560188,
            'upload_date': '20250922',
            'modified_timestamp': 1758563110,
            'modified_date': '20250922',
            '_old_archive_ids': ['rtp e877072'],
        },
        'params': {'noplaylist': True},
    }, {
        # Unambiguous URL for 2nd part of a multi-part episode
        'url': 'https://www.rtp.pt/play/p14335/e877072/a-nossa-tarde/1364744',
        'md5': 'b624767af558a557372a6fcd1dcdfa17',
        'info_dict': {
            'id': '1364744',
            'ext': 'mp4',
            'title': 'A Nossa Tarde',
            'duration': 3270.0,
            'thumbnail': r're:https://cdn-images\.rtp\.pt/multimedia/screenshots/p14335/p14335_2_20250922165718e161t0412\.jpg',
            'series': 'A Nossa Tarde',
            'series_id': 'p14335',
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

    def _extract_asset(self, asset_data, episode_id, episode_info, archive_compat=False):
        asset_id = asset_data['asset_id']
        asset_urls = traverse_obj(asset_data, ('asset_url', {dict}))
        media_urls = traverse_obj(asset_urls, (
            ((('hls', 'dash'), 'stream_url'), ('multibitrate', ('url_hls', 'url_dash'))),))
        formats, subtitles = self._extract_formats(media_urls, asset_id)

        for sub_data in traverse_obj(asset_urls, ('subtitles', 'vtt_list', lambda _, v: url_or_none(v['file']))):
            subtitles.setdefault(sub_data.get('code') or 'pt', []).append({
                'url': sub_data['file'],
                'name': sub_data.get('language'),
            })

        return {
            **episode_info,
            'id': asset_id,
            'episode_id': episode_id,
            # asset_id is a unique identifier for all RTP videos, while episode_id is duplicated
            # across all parts of a multi-part episode. Older versions of this IE returned
            # episode_id as the video id and would only download the first part of multi-part eps.
            # For download archive compat, we should return the episode_id as the old archive id
            # *only* when extracting single-part episodes OR the *first* part of a multi-part ep.
            '_old_archive_ids': [make_archive_id(self, episode_id)] if archive_compat else None,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(asset_data, {
                'thumbnail': ('asset_thumbnail', {url_or_none}),
                'duration': ('asset_duration', {parse_duration}),
                'webpage_url': ('web', 'url', {url_or_none}),
            }),
        }

    def _report_fallback_warning(self, missing_info_name='required info', display_id=None):
        self.report_warning(
            f'{missing_info_name.capitalize()} not found in API response; falling back to web extraction',
            video_id=display_id)

    def _entries(self, assets, episode_id, episode_info):
        # Only pass archive_compat=True for the first entry without an asset_id in its webpage_url
        for idx, asset_data in enumerate(assets):
            yield self._extract_asset(asset_data, episode_id, episode_info, archive_compat=not idx)

    def _extract_from_api(self, program_id, episode_id, asset_id):
        auth_token = self._fetch_auth_token()
        if not auth_token:
            self._report_fallback_warning('auth token', episode_id)
            return None

        episode_data = traverse_obj(self._download_json(
            f'https://www.rtp.pt/play/api/1/get-episode/{program_id[1:]}/{episode_id[1:]}',
            asset_id or episode_id, query={'include_assets': 'true', 'include_webparams': 'true'},
            headers={
                'Accept': '*/*',
                'Authorization': f'Bearer {auth_token}',
                'User-Agent': self._USER_AGENT,
            }, fatal=False), 'result', {dict})
        if not episode_data:
            self._report_fallback_warning('episode data', episode_id)
            return None

        episode_info = {
            'id': episode_id,  # playlist id
            'episode_id': episode_id,
            'series_id': program_id,
            **traverse_obj(episode_data, ('episode', {
                'title': (('episode_title', 'program_title'), {str}, filter, any),
                'alt_title': ('episode_subtitle', {str}, filter),
                'description': (('episode_description', 'episode_summary'), {str}, filter, any),
                'timestamp': ('episode_air_date', {parse_iso8601(delimiter=' ')}),
                'modified_timestamp': ('episode_lastchanged', {parse_iso8601(delimiter=' ')}),
                'duration': ('episode_duration_complete', {parse_duration}),  # playlist duration
                'episode': ('episode_title', {str}, filter),
                'episode_number': ('episode_number', {int_or_none}),
                'season': ('program_season', {str}, filter),
                'series': ('program_title', {str}, filter),
            })),
        }

        assets = traverse_obj(episode_data, ('assets', lambda _, v: v['asset_id']))
        if not assets:
            self._report_fallback_warning('asset IDs', episode_id)
            return None

        if asset_id:
            asset_data = traverse_obj(assets, (lambda _, v: v['asset_id'] == asset_id, any))
            if not asset_data:
                self._report_fallback_warning(f'asset {asset_id}', episode_id)
                return None
            return self._extract_asset(asset_data, episode_id, episode_info)

        asset_data = assets[0]

        if self._yes_playlist(
            len(assets) > 1 and episode_id, asset_data['asset_id'],
            playlist_label='multi-part episode', video_label='individual part',
        ):
            return self.playlist_result(
                self._entries(assets, episode_id, episode_info), **episode_info)

        # Pass archive_compat=True so we return _old_archive_ids for URLs without an asset_id
        return self._extract_asset(asset_data, episode_id, episode_info, archive_compat=True)

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

    def _extract_from_html(self, url, program_id, episode_id, asset_id):
        webpage = self._download_webpage(url, asset_id or episode_id)
        if not asset_id:
            asset_id = self._search_regex(r'\basset_id\s*:\s*"(\d+)"', webpage, 'asset ID')
            old_archive_ids = [make_archive_id(self, episode_id)]
        else:
            old_archive_ids = None

        formats = []
        subtitles = {}
        media_urls = traverse_obj(re.findall(r'(?:var\s+f\s*=|RTPPlayer\({[^}]+file:)\s*({[^}]+}|"[^"]+")', webpage), (
            -1, (({self.__unobfuscate}, {js_to_json}, {json.loads}, {dict.values}, ...), {json.loads})))
        formats, subtitles = self._extract_formats(media_urls, asset_id)

        return {
            'id': asset_id,
            'episode_id': episode_id,
            'series_id': program_id,
            'formats': formats,
            'subtitles': subtitles,
            'description': self._html_search_meta(['og:description', 'twitter:description'], webpage, default=None),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage, default=None),
            **self._search_json_ld(webpage, asset_id, default={}),
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage, default=None),
            '_old_archive_ids': old_archive_ids,
        }

    def _real_extract(self, url):
        program_id, episode_id, asset_id = self._match_valid_url(url).group('program_id', 'episode_id', 'asset_id')
        return (
            self._extract_from_api(program_id, episode_id, asset_id)
            or self._extract_from_html(url, program_id, episode_id, asset_id))
