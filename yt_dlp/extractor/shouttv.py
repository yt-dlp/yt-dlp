import itertools
import json
import re
import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    filter_dict,
    int_or_none,
    jwt_decode_hs256,
    parse_age_limit,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class ShoutTVBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'shouttv'
    _API_BASE_URL = 'https://dce-frontoffice.imggaming.com/api'
    # version and key taken from https://watch.shout-tv.com/code/js/app.3b4ef510d0048f672e1d.js
    _APP_VERSION = '6.57.10.65bab8b'  # 'OUTPUT_FOLDER' in JS
    _API_KEY = '857a1e5d-e35e-4fdf-805b-a87b6f8364bf'  # 'API_KEY' in JS
    _API_REALM = 'dce.shout'
    _API_HEADERS = {
        'Accept': 'application/json',
        'Origin': 'https://watch.shout-tv.com',
        'Referer': 'https://watch.shout-tv.com/',
        'app': 'dice',
        'x-api-key': _API_KEY,
        'x-app-var': _APP_VERSION,
    }
    _ACCESS_TOKEN = None
    _ACCESS_EXPIRY = 0
    _REFRESH_TOKEN = None
    _is_logged_in = False

    def _set_tokens(self, auth_data):
        ShoutTVBaseIE._ACCESS_TOKEN = auth_data['authorisationToken']  # 10 minute TTL
        ShoutTVBaseIE._ACCESS_EXPIRY = jwt_decode_hs256(ShoutTVBaseIE._ACCESS_TOKEN)['exp']
        if refresh_token := traverse_obj(auth_data, ('refreshToken', {str})):
            self.write_debug('New refresh token granted')
            ShoutTVBaseIE._REFRESH_TOKEN = refresh_token  # 2 month TTL
        username, _ = self._get_login_info()
        if username and ShoutTVBaseIE._is_logged_in:
            self.cache.store(self._NETRC_MACHINE, 'tokens', {
                username: [ShoutTVBaseIE._ACCESS_TOKEN, ShoutTVBaseIE._REFRESH_TOKEN],
            })

    def _fetch_access_token(self, content_id=None):
        if ShoutTVBaseIE._ACCESS_TOKEN and ShoutTVBaseIE._ACCESS_EXPIRY - 10 > time.time():
            return

        headers = self._API_HEADERS.copy()
        if ShoutTVBaseIE._REFRESH_TOKEN and ShoutTVBaseIE._ACCESS_TOKEN:
            headers.update({
                'Authorization': f'Mixed {ShoutTVBaseIE._ACCESS_TOKEN} {ShoutTVBaseIE._REFRESH_TOKEN}',
                'Realm': self._API_REALM,
            })
        self._set_tokens(self._download_json(
            f'{self._API_BASE_URL}/v1/init/', content_id,
            'Fetching access token', 'Unable to fetch token',
            headers=headers, query={
                'lk': 'language',
                'pk': ['subTitleLanguage', 'audioLanguage', 'autoAdvance', 'pluginAccessTokens'],
                'readLicences': 'true',
                'countEvents': 'LIVE',
                'menuTargetPlatform': 'WEB',
            })['authentication'])

    def _perform_login(self, username, password):
        self.report_login()
        cached_tokens = self.cache.load(self._NETRC_MACHINE, 'tokens', default={}).get(username) or []
        if (len(cached_tokens) == 2) and (jwt_decode_hs256(cached_tokens[1])['exp'] - 60 > time.time()):
            ShoutTVBaseIE._ACCESS_TOKEN, ShoutTVBaseIE._REFRESH_TOKEN = cached_tokens
            ShoutTVBaseIE._is_logged_in = True
            self.write_debug('Cached refresh token is still valid')
            return

        self._fetch_access_token()
        try:
            login_data = self._download_json(
                f'{self._API_BASE_URL}/v2/login', None, 'Submitting credentials',
                'Unable to log in', headers={
                    **self._API_HEADERS,
                    'Authorization': f'Bearer {ShoutTVBaseIE._ACCESS_TOKEN}',
                    'Content-Type': 'application/json',
                    'Realm': self._API_REALM,
                }, data=json.dumps({
                    'id': username,
                    'secret': password,
                }, separators=(',', ':')).encode())
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                raise ExtractorError('Invalid username or password', expected=True)
            raise
        ShoutTVBaseIE._is_logged_in = True
        self._set_tokens(login_data)

    def _call_api(self, content_id, content_type, note='API JSON', query=None, headers=None):
        endpoint = {
            'video': 'vod',
            'live': 'event',
        }.get(content_type, content_type)
        self._fetch_access_token(content_id)
        return self._download_json(
            f'{self._API_BASE_URL}/v4/{endpoint}/{content_id}', content_id,
            f'Downloading {note}', f'Unable to download {note}', query=query,
            headers={
                **self._API_HEADERS,
                'Authorization': f'Bearer {ShoutTVBaseIE._ACCESS_TOKEN}',
                **(headers or {}),
                'Realm': self._API_REALM,
            })

    @staticmethod
    def _parse_details(details):
        return traverse_obj(details, {
            'id': ('id', {int}, {str_or_none}),
            'title': ('title', {str}),
            'description': ('description', {str}),
            'duration': ('duration', {int_or_none}),
            'categories': ('categories', ..., {str}, filter),
            'thumbnails': (('thumbnailUrl', 'posterUrl', 'coverUrl'), {'url': {url_or_none}}),
            'age_limit': (('rating', 'contentRating'), 'rating', {parse_age_limit}, any),
            'episode_number': ('episodeInformation', 'episodeNumber', {int_or_none}),
            'season_number': ('episodeInformation', 'seasonNumber', {int_or_none}),
            'season_id': ('episodeInformation', 'season', {int}, {str_or_none}),
            'season': ('episodeInformation', 'seasonTitle', {str}),
            'series_id': ('episodeInformation', 'seriesInformation', 'id', {int}, {str_or_none}),
            'series': ('episodeInformation', 'seriesInformation', 'title', {str}),
        })

    def _extract_vod_formats_and_subtitles(self, player, video_id):
        formats, subtitles = [], {}
        # XXX: 'subtitles' array fields are alongside the 'url' fields in both 'hls and 'dash',
        #      but couldn't find any examples where the arrays were not empty
        for idx, m3u8_url in enumerate(traverse_obj(player, ('hls', ..., 'url', {url_or_none})), start=1):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, 'mp4', m3u8_id=f'hls-{idx}', fatal=False)
            # This site's HLS manifests do not provide any audio codec/bitrate info
            # The audio formats are given a GROUP-ID to pair them to video formats w/the same GROUP-ID
            # Worst quality audio is paired to worst quality video, ba paired to bv, etc
            # 'audio-1' is usually the worst quality and 'audio-3' is usually the best quality
            for fmt in fmts:
                if mobj := re.search(r'-audio-(?P<quality>\d+)', fmt['format_id']):
                    fmt['quality'] = int(mobj.group('quality'))
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        for idx, mpd_url in enumerate(traverse_obj(player, ('dash', ..., 'url', {url_or_none})), start=1):
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                mpd_url, video_id, mpd_id=f'dash-{idx}', fatal=False)
            # DASH audio formats will always be sorted below HLS unless we also set 'quality'
            for q, fmt in enumerate(sorted(traverse_obj(fmts, (
                    lambda _, v: v['tbr'] and v['vcodec'] == 'none')), key=lambda x: x['tbr'])):
                fmt['quality'] = q
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return formats, subtitles


class ShoutTVIE(ShoutTVBaseIE):
    IE_NAME = 'shouttv'
    IE_DESC = 'Shout! TV video-on-demand on live channels'
    _VALID_URL = r'https?://watch\.shout-tv\.com/(?P<type>video|live)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://watch.shout-tv.com/video/640292',
        'info_dict': {
            'id': '640292',
            'ext': 'mp4',
            'title': 'Pee-wee\'s Playhouse Christmas Special',
            'description': 'Pee-Wee Herman throws a Christmas party at his playhouse with his friends and some celebrity guests.',
            'duration': 2879,
            'thumbnail': 'https://dve-images.imggaming.com/original/p/2024/05/30/HE2kpg3EjcjrQJb2dSctUVhzpyz7rCXn-1717027231485.jpg',
            'age_limit': 0,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://watch.shout-tv.com/video/691416?seasonId=26337',
        'info_dict': {
            'id': '691416',
            'ext': 'mp4',
            'title': 'The Commish: S1 E1 - In The Best Of Families',
            'description': 'md5:d61403fb8ddaaeb1100228ac146f5a0c',
            'episode': 'Episode 0',
            'episode_number': 0,
            'season': 'The Commish: Season 1',
            'season_number': 1,
            'season_id': '26337',
            'series': 'The Commish',
            'series_id': '2695',
            'duration': 2785,
            'thumbnail': 'https://dve-images.imggaming.com/original/p/2024/09/23/wgpGQ1Vr3DPG6sHnmbGpsKZqMkcosJND-1727130957509.jpg',
            'age_limit': 14,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://watch.shout-tv.com/live/265692',
        'info_dict': {
            'id': '265692',
            'ext': 'mp4',
            'title': r're:MST3K \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'live_status': 'is_live',
            'thumbnail': 'https://img.dge-prod.dicelaboratory.com/thumbnails/265692/original/latest.jpg',
        },
        'params': {'skip_download': 'livestream'},
    }]

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        details = self._call_api(
            video_id, video_type, query={'includePlaybackDetails': 'URL'},
            headers={
                'CM-APP-NAME': 'Website',
                'CM-APP-VERSION': self._APP_VERSION,
                'CM-CST-TCF': '',
                'CM-CST-USP': '',
                'CM-DVC-DNT': '1',
                'CM-DVC-H': '1080',
                'CM-DVC-LANG': 'en-US',
                'CM-DVC-OS': '14',
                'CM-DVC-TYPE': '2',
                'CM-DVC-W': '1920',
                'CM-WEB-MBL': '0',
                'CM-WEB-PAGE': f'/{video_type}/{video_id}',
            })

        access_level = traverse_obj(details, ('accessLevel', {str}))
        if access_level == 'GRANTED_ON_SIGN_IN':
            self.raise_login_required(method='password')
        elif access_level != 'GRANTED':
            self.report_warning(f'Unknown access level "{access_level}"')

        player = self._download_json(
            details['playerUrlCallback'], video_id, 'Downloading player JSON',
            'Unable to download player JSON', headers={'Accept': 'application/json'})
        is_live = {
            'VOD': False,
            'LIVE': True,
        }.get(details.get('type'), video_type == 'live')

        if is_live:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                player['hlsUrl'], video_id, 'mp4', m3u8_id='hls', live=True)
        else:
            formats, subtitles = self._extract_vod_formats_and_subtitles(player, video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            **self._parse_details(details),
        }


class ShoutTVPlaylistBaseIE(ShoutTVBaseIE):
    """Subclasses must set _PAGE_SIZE, _PLAYLIST_TYPE, _ENTRIES_KEY"""

    def _create_entry(self, entry):
        raise NotImplementedError('This method must be implemented by subclasses')

    def _fetch_page(self, playlist_id, page=1, last_seen=None):
        return self._call_api(
            playlist_id, self._PLAYLIST_TYPE, note=f'{self._PLAYLIST_TYPE} page {page}',
            query=filter_dict({'rpp': self._PAGE_SIZE, 'lastSeen': last_seen}))

    def _entries(self, playlist_id, first_page):
        last_seen = None
        for page in itertools.count(1):
            data = first_page if page == 1 else self._fetch_page(playlist_id, page, last_seen)
            for entry in traverse_obj(data, (self._ENTRIES_KEY, lambda _, v: v['id'] is not None)):
                yield self._create_entry(entry)

            last_seen = traverse_obj(data, ('paging', 'lastSeen', {int}, {str_or_none}))
            if not traverse_obj(data, ('paging', 'moreDataAvailable', {bool})) or not last_seen:
                break

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        first_page = self._fetch_page(playlist_id)

        return self.playlist_result(
            self._entries(playlist_id, first_page), playlist_id,
            **traverse_obj(first_page, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnails': (('titleUrl', 'posterUrl', 'coverUrl'), {'url': {url_or_none}}),
                'series': ('series', 'title', {str}),
                'series_id': ('series', 'seriesId', {int}, {str_or_none}),
                'season_number': (
                    'seasonNumber', {int_or_none},
                    {lambda x: x if self._PLAYLIST_TYPE == 'season' else None}),
            }))


class ShoutTVSeasonIE(ShoutTVPlaylistBaseIE):
    IE_NAME = 'shouttv:season'
    IE_DESC = 'Shout! TV seasons'
    _VALID_URL = r'https?://watch\.shout-tv\.com/season/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://watch.shout-tv.com/season/26338',
        'info_dict': {
            'id': '26338',
            'title': 'The Commish: Season 2',
            'description': 'md5:a5f99159e36d23af97a63137712c3b04',
            'series': 'The Commish',
            'series_id': '2695',
            'season_number': 2,
        },
        'playlist_count': 22,
    }]
    _PAGE_SIZE = 5
    _PLAYLIST_TYPE = 'season'
    _ENTRIES_KEY = 'episodes'

    def _create_entry(self, entry):
        return self.url_result(
            f'https://watch.shout-tv.com/video/{entry["id"]}', ShoutTVIE,
            **self._parse_details(entry))


class ShoutTVSeriesIE(ShoutTVPlaylistBaseIE):
    IE_NAME = 'shouttv:series'
    IE_DESC = 'Shout! TV series'
    _VALID_URL = r'https?://watch\.shout-tv\.com/series/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://watch.shout-tv.com/series/2695',
        'info_dict': {
            'id': '2695',
            'title': 'The Commish',
            'description': 'md5:a5f99159e36d23af97a63137712c3b04',
        },
        'playlist_count': 5,
    }]
    _PAGE_SIZE = 20
    _PLAYLIST_TYPE = 'series'
    _ENTRIES_KEY = 'seasons'

    def _create_entry(self, entry):
        return self.url_result(
            f'https://watch.shout-tv.com/season/{entry["id"]}', ShoutTVSeasonIE,
            **traverse_obj(entry, {
                'id': ('id', {int}, {str_or_none}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'season_id': ('id', {int}, {str_or_none}),
                'season_number': ('seasonNumber', {int_or_none}),
            }))
