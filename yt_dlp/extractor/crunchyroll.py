import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    format_field,
    int_or_none,
    join_nonempty,
    parse_age_limit,
    parse_iso8601,
    qualities,
    remove_start,
    time_seconds,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class CrunchyrollBaseIE(InfoExtractor):
    _BASE_URL = 'https://www.crunchyroll.com'
    _API_BASE = 'https://api.crunchyroll.com'
    _NETRC_MACHINE = 'crunchyroll'
    _AUTH_HEADERS = None
    _BASIC_AUTH = None
    _QUERY = None

    @property
    def is_logged_in(self):
        return self._get_cookies(self._BASE_URL).get('etp_rt')

    def _perform_login(self, username, password):
        if self.is_logged_in:
            return

        upsell_response = self._download_json(
            f'{self._API_BASE}/get_upsell_data.0.json', None, 'Getting session id',
            query={
                'sess_id': 1,
                'device_id': 'whatvalueshouldbeforweb',
                'device_type': 'com.crunchyroll.static',
                'access_token': 'giKq5eY27ny3cqz',
                'referer': f'{self._BASE_URL}/welcome/login'
            })
        if upsell_response['code'] != 'ok':
            raise ExtractorError('Could not get session id')
        session_id = upsell_response['data']['session_id']

        login_response = self._download_json(
            f'{self._API_BASE}/login.1.json', None, 'Logging in',
            data=urlencode_postdata({
                'account': username,
                'password': password,
                'session_id': session_id
            }))
        if login_response['code'] != 'ok':
            raise ExtractorError('Login failed. Server message: %s' % login_response['message'], expected=True)
        if not self.is_logged_in:
            raise ExtractorError('Login succeeded but did not set etp_rt cookie')

    def _update_query(self, lang):
        if not self._QUERY:
            self._QUERY = {}

        if lang in self._QUERY:
            return

        webpage = self._download_webpage(
            f'{self._BASE_URL}/{lang}', None, note=f'Retrieving main page (lang={lang or None})')

        initial_state = self._search_json(r'__INITIAL_STATE__\s*=', webpage, 'initial state', None)
        self._QUERY[lang] = traverse_obj(initial_state, {
            'locale': ('localization', 'locale'),
        }) or None

        if self._BASIC_AUTH:
            return

        app_config = self._search_json(r'__APP_CONFIG__\s*=', webpage, 'app config', None)
        cx_api_param = app_config['cxApiParams']['accountAuthClientId' if self.is_logged_in else 'anonClientId']
        self.write_debug(f'Using cxApiParam={cx_api_param}')
        self._BASIC_AUTH = 'Basic ' + base64.b64encode(f'{cx_api_param}:'.encode()).decode()

    def _update_auth(self):
        if self._AUTH_HEADERS and self._AUTH_REFRESH > time_seconds():
            return

        assert self._BASIC_AUTH, '_update_query needs to be called at least one time beforehand'
        grant_type = 'etp_rt_cookie' if self.is_logged_in else 'client_id'
        auth_response = self._download_json(
            f'{self._BASE_URL}/auth/v1/token', None, note=f'Authenticating with grant_type={grant_type}',
            headers={'Authorization': self._BASIC_AUTH}, data=f'grant_type={grant_type}'.encode())

        self._AUTH_HEADERS = {'Authorization': auth_response['token_type'] + ' ' + auth_response['access_token']}
        self._AUTH_REFRESH = time_seconds(seconds=traverse_obj(auth_response, ('expires_in', {float_or_none}), default=300) - 10)

    def _call_api(self, endpoint, internal_id, lang, note='api'):
        self._update_query(lang)
        self._update_auth()

        endpoint = remove_start(endpoint, 'cms:').lstrip('/')
        if not endpoint.startswith('content/v2/cms/'):
            endpoint = f'content/v2/cms/{endpoint}'

        return self._download_json(
            f'{self._BASE_URL}/{endpoint}', internal_id, f'Downloading {note} JSON',
            headers=self._AUTH_HEADERS, query=self._QUERY[lang])


class CrunchyrollBetaIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll'
    _VALID_URL = r'''(?x)
        https?://(?:beta\.|www\.)?crunchyroll\.com/
        (?P<lang>(?:\w{2}(?:-\w{2})?/)?)
        watch/(?P<id>\w+)'''
    _TESTS = [{
        # Premium only
        'url': 'https://www.crunchyroll.com/watch/GY2P1Q98Y/to-the-future',
        'info_dict': {
            'id': 'GY2P1Q98Y',
            'ext': 'mp4',
            'duration': 1380.241,
            'timestamp': 1459632600,
            'description': 'md5:a022fbec4fbb023d43631032c91ed64b',
            'title': 'World Trigger Episode 73 – To the Future',
            'upload_date': '20160402',
            'series': 'World Trigger',
            'series_id': 'GR757DMKY',
            'season': 'World Trigger',
            'season_id': 'GR9P39NJ6',
            'season_number': 1,
            'episode': 'To the Future',
            'episode_number': 73,
            'thumbnail': r're:^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
            'chapters': 'count:2',
            'age_limit': 14,
        },
        'params': {'skip_download': 'm3u8', 'format': 'all[format_id~=hardsub]'},
    }, {
        # Premium only
        'url': 'https://www.crunchyroll.com/watch/GYE5WKQGR',
        'info_dict': {
            'id': 'GYE5WKQGR',
            'ext': 'mp4',
            'duration': 366.459,
            'timestamp': 1476788400,
            'description': 'md5:74b67283ffddd75f6e224ca7dc031e76',
            'title': 'SHELTER – Porter Robinson presents Shelter the Animation',
            'upload_date': '20161018',
            'series': 'SHELTER',
            'series_id': 'GYGG09WWY',
            'season': 'SHELTER',
            'season_id': 'GR09MGK4R',
            'season_number': 1,
            'episode': 'Porter Robinson presents Shelter the Animation',
            'episode_number': 0,
            'thumbnail': r're:^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
            'age_limit': 14,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.crunchyroll.com/watch/GJWU2VKK3/cherry-blossom-meeting-and-a-coming-blizzard',
        'info_dict': {
            'id': 'GJWU2VKK3',
            'ext': 'mp4',
            'duration': 1420.054,
            'description': 'md5:2d1c67c0ec6ae514d9c30b0b99a625cd',
            'title': 'The Ice Guy and His Cool Female Colleague Episode 1 – Cherry Blossom Meeting and a Coming Blizzard',
            'series': 'The Ice Guy and His Cool Female Colleague',
            'series_id': 'GW4HM75NP',
            'season': 'The Ice Guy and His Cool Female Colleague',
            'season_id': 'GY9PC21VE',
            'season_number': 1,
            'episode': 'Cherry Blossom Meeting and a Coming Blizzard',
            'episode_number': 1,
            'chapters': 'count:2',
            'thumbnail': r're:^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
            'timestamp': 1672839000,
            'upload_date': '20230104',
            'age_limit': 14,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.crunchyroll.com/watch/GM8F313NQ',
        'info_dict': {
            'id': 'GM8F313NQ',
            'ext': 'mp4',
            'title': 'Garakowa -Restore the World-',
            'description': 'md5:8d2f8b6b9dd77d87810882e7d2ee5608',
            'duration': 3996.104,
            'age_limit': 13,
            'thumbnail': r're:^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.crunchyroll.com/watch/GY2P1Q98Y',
        'only_matching': True,
    }, {
        'url': 'https://beta.crunchyroll.com/pt-br/watch/G8WUN8VKP/the-ruler-of-conspiracy',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, internal_id = self._match_valid_url(url).group('lang', 'id')

        response = traverse_obj(self._call_api(
            f'objects/{internal_id}', internal_id, lang, 'object info'), ('data', 0, {dict}))
        if not response:
            raise ExtractorError('No item with the provided id could be found', expected=True)

        def raise_for_premium_required(object_type):
            if not traverse_obj(response, (f'{object_type}_metadata', 'is_premium_only')) or response.get('streams_link'):
                return
            message = f'This {object_type} is for premium members only'
            if self.is_logged_in:
                raise ExtractorError(message, expected=True)
            self.raise_login_required(message)

        object_type = response.get('type')
        if object_type == 'episode':
            raise_for_premium_required(object_type)
            result = self._transform_episode_response(response)
            result['formats'], result['subtitles'] = self._extract_streams(
                response['streams_link'], lang, internal_id)

            # if no intro chapter is available, a 403 without usable data is returned
            intro_chapter = self._download_json(
                f'https://static.crunchyroll.com/datalab-intro-v2/{internal_id}.json',
                internal_id, note='Downloading chapter info', fatal=False, errnote=False)
            if isinstance(intro_chapter, dict):
                result['chapters'] = [{
                    'title': 'Intro',
                    'start_time': float_or_none(intro_chapter.get('startTime')),
                    'end_time': float_or_none(intro_chapter.get('endTime')),
                }]

        elif object_type == 'movie':
            raise_for_premium_required(object_type)
            result = traverse_obj(response, {
                'id': 'id',
                'title': ('title', {str}),
                'description': ('description', {str}, {lambda x: x.replace(r'\r\n', '\n')}),
                'thumbnails': ('images', 'thumbnail', ..., ..., {
                    'url': ('source', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }),
                'duration': ('movie_metadata', 'duration_ms', {lambda x: float_or_none(x, 1000)}),
                'age_limit': ('movie_metadata', 'maturity_ratings', -1, {parse_age_limit}),
            })
            result['formats'], result['subtitles'] = self._extract_streams(
                response['streams_link'], lang, internal_id)

        elif object_type == 'movie_listing':
            raise ExtractorError('Movie listing object is not yet supported', expected=True)

        else:
            raise ExtractorError(f'Unknown object type {object_type}')

        return result

    def _extract_streams(self, path, lang='', display_id=None):
        stream_response = self._call_api(path, display_id, lang, 'stream info')
        get_streams = lambda *names: (traverse_obj(stream_response, (*names, {dict})) or {}).items()

        requested_formats = self._configuration_arg('format') or ['adaptive_hls']
        available_formats = {}
        for stream_type, streams in get_streams('data', 0):
            if stream_type not in requested_formats:
                continue
            for stream in streams.values():
                if not stream.get('url'):
                    continue
                hardsub_lang = stream.get('hardsub_locale') or ''
                format_id = join_nonempty(stream_type, format_field(stream, 'hardsub_locale', 'hardsub-%s'))
                available_formats[hardsub_lang] = (stream_type, format_id, hardsub_lang, stream['url'])

        requested_hardsubs = [('' if val == 'none' else val) for val in (self._configuration_arg('hardsub') or ['none'])]
        if '' in available_formats and 'all' not in requested_hardsubs:
            full_format_langs = set(requested_hardsubs)
            self.to_screen(
                'To get all formats of a hardsub language, use '
                '"--extractor-args crunchyrollbeta:hardsub=<language_code or all>". '
                'See https://github.com/yt-dlp/yt-dlp#crunchyrollbeta-crunchyroll for more info',
                only_once=True)
        else:
            full_format_langs = set(map(str.lower, available_formats))

        hardsub_preference = qualities(requested_hardsubs[::-1])
        formats = []
        for stream_type, format_id, hardsub_lang, stream_url in available_formats.values():
            if stream_type.endswith('hls'):
                if hardsub_lang.lower() in full_format_langs:
                    adaptive_formats = self._extract_m3u8_formats(
                        stream_url, display_id, 'mp4', m3u8_id=format_id,
                        fatal=False, note=f'Downloading {format_id} HLS manifest')
                else:
                    adaptive_formats = (self._m3u8_meta_format(stream_url, ext='mp4', m3u8_id=format_id),)
            elif stream_type.endswith('dash'):
                adaptive_formats = self._extract_mpd_formats(
                    stream_url, display_id, mpd_id=format_id,
                    fatal=False, note=f'Downloading {format_id} MPD manifest')
            else:
                self.report_warning(f'Encountered unknown stream_type: {stream_type!r}', display_id, only_once=True)
                continue
            for f in adaptive_formats:
                if f.get('acodec') != 'none':
                    f['language'] = stream_response.get('audio_locale')
                f['quality'] = hardsub_preference(hardsub_lang.lower())
            formats.extend(adaptive_formats)

        subtitles = {
            lang: [{
                'url': subtitle_data.get('url'),
                'ext': subtitle_data.get('format'),
            }] for lang, subtitle_data in get_streams('meta', 'subtitles')
        }

        return formats, subtitles

    @staticmethod
    def _transform_episode_response(data):
        metadata = traverse_obj(data, (('episode_metadata', None), {dict}), get_all=False) or {}
        return {
            'id': data['id'],
            'title': ' \u2013 '.join((
                ('%s%s' % (
                    format_field(metadata, 'season_title'),
                    format_field(metadata, 'episode', ' Episode %s'))),
                format_field(data, 'title'))),
            **traverse_obj(data, {
                'episode': ('title', {str}),
                'description': ('description', {str}, {lambda x: x.replace(r'\r\n', '\n')}),
                'thumbnails': ('images', 'thumbnail', ..., ..., {
                    'url': ('source', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }),
            }),
            **traverse_obj(metadata, {
                'duration': ('duration_ms', {lambda x: float_or_none(x, 1000)}),
                'timestamp': ('upload_date', {parse_iso8601}),
                'series': ('series_title', {str}),
                'series_id': ('series_id', {str}),
                'season': ('season_title', {str}),
                'season_id': ('season_id', {str}),
                'season_number': ('season_number', {float_or_none}),
                'episode_number': ('sequence_number', {float_or_none}),
                'age_limit': ('maturity_ratings', -1, {parse_age_limit}),
                'language': ('audio_locale', {str}),
            })
        }


class CrunchyrollBetaShowIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll:playlist'
    _VALID_URL = r'''(?x)
        https?://(?:beta\.|www\.)?crunchyroll\.com/
        (?P<lang>(?:\w{2}(?:-\w{2})?/)?)
        series/(?P<id>\w+)'''
    _TESTS = [{
        'url': 'https://www.crunchyroll.com/series/GY19NQ2QR/Girl-Friend-BETA',
        'info_dict': {
            'id': 'GY19NQ2QR',
            'title': 'Girl Friend BETA',
            'description': 'md5:99c1b22ee30a74b536a8277ced8eb750',
            # XXX: `thumbnail` does not get set from `thumbnails` in playlist
            #  'thumbnail': r're:^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
            'age_limit': 14,
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://beta.crunchyroll.com/it/series/GY19NQ2QR',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, internal_id = self._match_valid_url(url).group('lang', 'id')

        def entries():
            seasons_response = self._call_api(f'series/{internal_id}/seasons', internal_id, lang, 'seasons')
            for season in seasons_response['data']:
                episodes_response = self._call_api(
                    f'seasons/{season["id"]}/episodes', season.get("slug_title"), lang, 'episode list')
                for episode_response in traverse_obj(episodes_response, ('data', ..., {dict})):
                    yield self.url_result(
                        f'https://www.crunchyroll.com/{lang}watch/{episode_response["id"]}',
                        CrunchyrollBetaIE, **CrunchyrollBetaIE._transform_episode_response(episode_response))

        series_response = traverse_obj(self._call_api(f'series/{internal_id}', internal_id, lang, 'series'), ('data', 0))
        return self.playlist_result(
            entries(), internal_id,
            **traverse_obj(series_response, {
                'title': ('title', {str}),
                'description': ('description', {lambda x: x.replace(r'\r\n', '\n')}),
                'age_limit': ('maturity_ratings', -1, {parse_age_limit}),
                'thumbnails': ('images', ..., ..., ..., {
                    'url': ('source', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                })
            }))
