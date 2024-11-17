import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    jwt_decode_hs256,
    parse_codecs,
    try_get,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class DigitalConcertHallIE(InfoExtractor):
    IE_DESC = 'DigitalConcertHall extractor'
    _VALID_URL = r'https?://(?:www\.)?digitalconcerthall\.com/(?P<language>[a-z]+)/(?P<type>film|concert|work)/(?P<id>[0-9]+)-?(?P<part>[0-9]+)?'
    _NETRC_MACHINE = 'digitalconcerthall'
    _TESTS = [{
        'note': 'Playlist with only one video',
        'url': 'https://www.digitalconcerthall.com/en/concert/53201',
        'info_dict': {
            'id': '53201-1',
            'ext': 'mp4',
            'composer': 'Kurt Weill',
            'title': '[Magic Night]',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
            'upload_date': '20210624',
            'timestamp': 1624548600,
            'duration': 2798,
            'album_artists': ['Members of the Berliner Philharmoniker', 'Simon Rössler'],
            'composers': ['Kurt Weill'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'Concert with several works and an interview',
        'url': 'https://www.digitalconcerthall.com/en/concert/53785',
        'info_dict': {
            'id': '53785',
            'album_artists': ['Berliner Philharmoniker', 'Kirill Petrenko'],
            'title': 'Kirill Petrenko conducts Mendelssohn and Shostakovich',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
        'playlist_count': 3,
    }, {
        'url': 'https://www.digitalconcerthall.com/en/film/388',
        'info_dict': {
            'id': '388',
            'ext': 'mp4',
            'title': 'The Berliner Philharmoniker and Frank Peter Zimmermann',
            'description': 'md5:cfe25a7044fa4be13743e5089b5b5eb2',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
            'upload_date': '20220714',
            'timestamp': 1657785600,
            'album_artists': ['Frank Peter Zimmermann', 'Benedikt von Bernstorff', 'Jakob von Bernstorff'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'Concert with several works and an interview',
        'url': 'https://www.digitalconcerthall.com/en/work/53785-1',
        'info_dict': {
            'id': '53785',
            'album_artists': ['Berliner Philharmoniker', 'Kirill Petrenko'],
            'title': 'Kirill Petrenko conducts Mendelssohn and Shostakovich',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
        'playlist_count': 1,
    }]
    _LOGIN_HINT = ('Use  --username token --password ACCESS_TOKEN  where ACCESS_TOKEN'
                   'is the `access_token_production` from your browser local storage')
    _REFRESH_HINT = 'or else use a refresh_token with  --username refresh --password REFRESH_TOKEN'
    _OAUTH_URL = 'https://api.digitalconcerthall.com/v2/oauth2/token'
    _CLIENT_ID = 'dch.webapp'
    _CLIENT_SECRET = '2ySLN+2Fwb'
    _USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15'
    _OAUTH_HEADERS = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Origin': 'https://www.digitalconcerthall.com',
        'Referer': 'https://www.digitalconcerthall.com/',
        'User-Agent': _USER_AGENT,
    }
    _real_access_token = None
    _access_token_expiry = 0
    _refresh_token = None

    @property
    def _access_token_is_expired(self):
        return self._access_token_expiry - 30 <= int(time.time())

    @property
    def _access_token(self):
        if not self._real_access_token:
            # return an initial access token that can be used to auth with password or refresh_token
            return self._download_json(
                self._OAUTH_URL, None, 'Obtaining initial token', 'Unable to obtain initial token',
                data=urlencode_postdata({
                    'affiliate': 'none',
                    'grant_type': 'device',
                    'device_vendor': 'unknown',
                    # device_model 'Safari' gets split streams of 4K/HEVC video and lossless/FLAC audio,
                    # but this is no longer effective since actual login is not possible anymore
                    'device_model': 'unknown',
                    'app_id': self._CLIENT_ID,
                    'app_distributor': 'berlinphil',
                    'app_version': '1.95.0',
                    'client_secret': self._CLIENT_SECRET,
                }), headers=self._OAUTH_HEADERS)['access_token']

        if self._access_token_is_expired:
            if not self._refresh_token:
                raise ExtractorError(
                    'Access token has expired. Get a new access_token from your browser '
                    f'and try again, {self._REFRESH_HINT}', expected=True)
            self._fetch_new_tokens()

        return self._real_access_token

    @_access_token.setter
    def _access_token(self, value):
        self._real_access_token = value
        self._access_token_expiry = traverse_obj(value, ({jwt_decode_hs256}, 'exp', {int})) or 0

    def _set_tokens(self, auth_data):
        self._access_token = auth_data['access_token']
        if refresh_token := traverse_obj(auth_data, ('refresh_token', {str})):
            self.write_debug('New refresh token granted')
            self._refresh_token = refresh_token
        self.cache.store(self._NETRC_MACHINE, 'tokens', {
            'access_token': self._real_access_token,
            'refresh_token': self._refresh_token,
        })

    def _fetch_new_tokens(self):
        try:
            response = self._download_json(
                self._OAUTH_URL, None, 'Refreshing token', 'Unable to refresh token',
                data=urlencode_postdata({
                    'grant_type': 'refresh_token',
                    'refresh_token': self._refresh_token,
                    'client_id': self._CLIENT_ID,
                    'client_secret': self._CLIENT_SECRET,
                }), headers={
                    **self._OAUTH_HEADERS,
                    'Authorization': f'Bearer {self._real_access_token or self._access_token}',
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                self._refresh_token = None
                self._set_tokens({'access_token': None})
                raise ExtractorError('Your tokens have been invalidated', expected=True)
            raise
        self._set_tokens(response)

    def _perform_login(self, username, password):
        if username not in ('refresh', 'token'):
            raise ExtractorError(
                'Login with username and password is no longer supported '
                f'for this site. {self._LOGIN_HINT}, {self._REFRESH_HINT}', expected=True)
        self.report_login()

        # Try first with passed refresh_token since user may want to override the cache with it
        if username == 'refresh':
            self._refresh_token = password
            self._fetch_new_tokens()
            return

        # Try cached access_token
        cached_tokens = self.cache.load(self._NETRC_MACHINE, 'tokens', default={})
        self._access_token = cached_tokens.get('access_token')
        self._refresh_token = cached_tokens.get('refresh_token')
        if not self._access_token_is_expired:
            return
        if self._real_access_token:
            self.write_debug('Cached access token has expired, invalidating')
            self._access_token = None
        # Try cached refresh_token
        if self._refresh_token:
            try:
                return self._fetch_new_tokens()
            except ExtractorError:
                # Do not raise for caached tokens; invalidate and continue
                self._access_token = None

        # username is 'token'
        if not traverse_obj(password, {jwt_decode_hs256}):
            raise ExtractorError(
                f'The access token passed to yt-dlp is not valid. {self._LOGIN_HINT}', expected=True)
        self._access_token = password
        self._set_tokens({'access_token': self._access_token})

    def _real_initialize(self):
        if not self._real_access_token:
            self.raise_login_required(f'{self._LOGIN_HINT}, {self._REFRESH_HINT}', method='none')

    def _entries(self, items, language, type_, **kwargs):
        for item in items:
            video_id = item['id']

            for retry in (False, True):
                try:
                    stream_info = self._download_json(
                        self._proto_relative_url(item['_links']['streams']['href']), video_id, headers={
                            'Accept': 'application/json',
                            'Authorization': f'Bearer {self._access_token}',
                            'Accept-Language': language,
                            'User-Agent': self._USER_AGENT,
                        })
                    break
                except ExtractorError as error:
                    if not retry and isinstance(error.cause, HTTPError) and error.cause.status == 401:
                        self.report_warning('Access token has been invalidated')
                        self._fetch_new_tokens()
                        continue
                    raise

            formats = []
            for m3u8_url in traverse_obj(stream_info, ('channel', ..., 'stream', ..., 'url', {url_or_none})):
                formats.extend(self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
            for fmt in formats:
                if fmt.get('format_note') and fmt.get('vcodec') == 'none':
                    fmt.update(parse_codecs(fmt['format_note']))

            yield {
                'id': video_id,
                'title': item.get('title'),
                'composer': item.get('name_composer'),
                'formats': formats,
                'duration': item.get('duration_total'),
                'timestamp': traverse_obj(item, ('date', 'published')),
                'description': item.get('short_description') or stream_info.get('short_description'),
                **kwargs,
                'chapters': [{
                    'start_time': chapter.get('time'),
                    'end_time': try_get(chapter, lambda x: x['time'] + x['duration']),
                    'title': chapter.get('text'),
                } for chapter in item['cuepoints']] if item.get('cuepoints') and type_ == 'concert' else None,
            }

    def _real_extract(self, url):
        language, type_, video_id, part = self._match_valid_url(url).group('language', 'type', 'id', 'part')
        if not language:
            language = 'en'

        api_type = 'concert' if type_ == 'work' else type_
        vid_info = self._download_json(
            f'https://api.digitalconcerthall.com/v2/{api_type}/{video_id}', video_id, headers={
                'Accept': 'application/json',
                'Accept-Language': language,
                'User-Agent': self._USER_AGENT,
                'Authorization': f'Bearer {self._access_token}',
            })
        videos = [vid_info] if type_ == 'film' else traverse_obj(vid_info, ('_embedded', ..., ...))

        if type_ == 'work':
            videos = [videos[int(part) - 1]]

        album_artists = traverse_obj(vid_info, ('_links', 'artist', ..., 'name', {str}))
        thumbnail = traverse_obj(vid_info, (
            'image', ..., {self._proto_relative_url}, {url_or_none},
            {lambda x: x.format(width=0, height=0)}, any))  # NB: 0x0 is the original size

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': vid_info.get('title'),
            'entries': self._entries(
                videos, language, type_, thumbnail=thumbnail, album_artists=album_artists),
            'thumbnail': thumbnail,
            'album_artists': album_artists,
        }
