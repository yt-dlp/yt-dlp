import base64
import uuid

from .common import InfoExtractor
from ..networking import Request
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    format_field,
    int_or_none,
    jwt_decode_hs256,
    parse_age_limit,
    parse_count,
    parse_iso8601,
    qualities,
    time_seconds,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class CrunchyrollBaseIE(InfoExtractor):
    _BASE_URL = 'https://www.crunchyroll.com'
    _API_BASE = 'https://api.crunchyroll.com'
    _NETRC_MACHINE = 'crunchyroll'
    _SWITCH_USER_AGENT = 'Crunchyroll/1.8.0 Nintendo Switch/12.3.12.0 UE4/4.27'
    _REFRESH_TOKEN = None
    _AUTH_HEADERS = None
    _AUTH_EXPIRY = None
    _API_ENDPOINT = None
    _BASIC_AUTH = 'Basic ' + base64.b64encode(':'.join((
        't-kdgp2h8c3jub8fn0fq',
        'yfLDfMfrYvKXh4JXS1LEI2cCqu1v5Wan',
    )).encode()).decode()
    _IS_PREMIUM = None
    _LOCALE_LOOKUP = {
        'ar': 'ar-SA',
        'de': 'de-DE',
        '': 'en-US',
        'es': 'es-419',
        'es-es': 'es-ES',
        'fr': 'fr-FR',
        'it': 'it-IT',
        'pt-br': 'pt-BR',
        'pt-pt': 'pt-PT',
        'ru': 'ru-RU',
        'hi': 'hi-IN',
    }

    def _set_auth_info(self, response):
        CrunchyrollBaseIE._IS_PREMIUM = 'cr_premium' in traverse_obj(response, ('access_token', {jwt_decode_hs256}, 'benefits', ...))
        CrunchyrollBaseIE._AUTH_HEADERS = {'Authorization': response['token_type'] + ' ' + response['access_token']}
        CrunchyrollBaseIE._AUTH_EXPIRY = time_seconds(seconds=traverse_obj(response, ('expires_in', {float_or_none}), default=300) - 10)

    def _request_token(self, headers, data, note='Requesting token', errnote='Failed to request token'):
        try:
            return self._download_json(
                f'{self._BASE_URL}/auth/v1/token', None, note=note, errnote=errnote,
                headers=headers, data=urlencode_postdata(data), impersonate=True)
        except ExtractorError as error:
            if not isinstance(error.cause, HTTPError) or error.cause.status != 403:
                raise
            if target := error.cause.response.extensions.get('impersonate'):
                raise ExtractorError(f'Got HTTP Error 403 when using impersonate target "{target}"')
            raise ExtractorError(
                'Request blocked by Cloudflare. '
                'Install the required impersonation dependency if possible, '
                'or else navigate to Crunchyroll in your browser, '
                'then pass the fresh cookies (with --cookies-from-browser or --cookies) '
                'and your browser\'s User-Agent (with --user-agent)', expected=True)

    def _perform_login(self, username, password):
        if not CrunchyrollBaseIE._REFRESH_TOKEN:
            CrunchyrollBaseIE._REFRESH_TOKEN = self.cache.load(self._NETRC_MACHINE, username)
        if CrunchyrollBaseIE._REFRESH_TOKEN:
            return

        try:
            login_response = self._request_token(
                headers={'Authorization': self._BASIC_AUTH}, data={
                    'username': username,
                    'password': password,
                    'grant_type': 'password',
                    'scope': 'offline_access',
                }, note='Logging in', errnote='Failed to log in')
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 401:
                raise ExtractorError('Invalid username and/or password', expected=True)
            raise

        CrunchyrollBaseIE._REFRESH_TOKEN = login_response['refresh_token']
        self.cache.store(self._NETRC_MACHINE, username, CrunchyrollBaseIE._REFRESH_TOKEN)
        self._set_auth_info(login_response)

    def _update_auth(self):
        if CrunchyrollBaseIE._AUTH_HEADERS and CrunchyrollBaseIE._AUTH_EXPIRY > time_seconds():
            return

        auth_headers = {'Authorization': self._BASIC_AUTH}
        if CrunchyrollBaseIE._REFRESH_TOKEN:
            data = {
                'refresh_token': CrunchyrollBaseIE._REFRESH_TOKEN,
                'grant_type': 'refresh_token',
                'scope': 'offline_access',
            }
        else:
            data = {'grant_type': 'client_id'}
            auth_headers['ETP-Anonymous-ID'] = uuid.uuid4()
        try:
            auth_response = self._request_token(auth_headers, data)
        except ExtractorError as error:
            username, password = self._get_login_info()
            if not username or not isinstance(error.cause, HTTPError) or error.cause.status != 400:
                raise
            self.to_screen('Refresh token has expired. Re-logging in')
            CrunchyrollBaseIE._REFRESH_TOKEN = None
            self.cache.store(self._NETRC_MACHINE, username, None)
            self._perform_login(username, password)
            return

        self._set_auth_info(auth_response)

    def _locale_from_language(self, language):
        config_locale = self._configuration_arg('metadata', ie_key=CrunchyrollBetaIE, casesense=True)
        return config_locale[0] if config_locale else self._LOCALE_LOOKUP.get(language)

    def _call_base_api(self, endpoint, internal_id, lang, note=None, query={}):
        self._update_auth()

        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'

        query = query.copy()
        locale = self._locale_from_language(lang)
        if locale:
            query['locale'] = locale

        return self._download_json(
            f'{self._BASE_URL}{endpoint}', internal_id, note or f'Calling API: {endpoint}',
            headers=CrunchyrollBaseIE._AUTH_HEADERS, query=query)

    def _call_api(self, path, internal_id, lang, note='api', query={}):
        if not path.startswith(f'/content/v2/{self._API_ENDPOINT}/'):
            path = f'/content/v2/{self._API_ENDPOINT}/{path}'

        try:
            result = self._call_base_api(
                path, internal_id, lang, f'Downloading {note} JSON ({self._API_ENDPOINT})', query=query)
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 404:
                return None
            raise

        if not result:
            raise ExtractorError(f'Unexpected response when downloading {note} JSON')
        return result

    def _extract_chapters(self, internal_id):
        # if no skip events are available, a 403 xml error is returned
        skip_events = self._download_json(
            f'https://static.crunchyroll.com/skip-events/production/{internal_id}.json',
            internal_id, note='Downloading chapter info', fatal=False, errnote=False)
        if not skip_events:
            return None

        chapters = []
        for event in ('recap', 'intro', 'credits', 'preview'):
            start = traverse_obj(skip_events, (event, 'start', {float_or_none}))
            end = traverse_obj(skip_events, (event, 'end', {float_or_none}))
            # some chapters have no start and/or ending time, they will just be ignored
            if start is None or end is None:
                continue
            chapters.append({'title': event.capitalize(), 'start_time': start, 'end_time': end})

        return chapters

    def _extract_stream(self, identifier, display_id=None):
        if not display_id:
            display_id = identifier

        self._update_auth()
        headers = {**CrunchyrollBaseIE._AUTH_HEADERS, 'User-Agent': self._SWITCH_USER_AGENT}
        try:
            stream_response = self._download_json(
                f'https://cr-play-service.prd.crunchyrollsvc.com/v1/{identifier}/console/switch/play',
                display_id, note='Downloading stream info', errnote='Failed to download stream info', headers=headers)
        except ExtractorError as error:
            if self.get_param('ignore_no_formats_error'):
                self.report_warning(error.orig_msg)
                return [], {}
            elif isinstance(error.cause, HTTPError) and error.cause.status == 420:
                raise ExtractorError(
                    'You have reached the rate-limit for active streams; try again later', expected=True)
            raise

        available_formats = {'': ('', '', stream_response['url'])}
        for hardsub_lang, stream in traverse_obj(stream_response, ('hardSubs', {dict.items}, lambda _, v: v[1]['url'])):
            available_formats[hardsub_lang] = (f'hardsub-{hardsub_lang}', hardsub_lang, stream['url'])

        requested_hardsubs = [('' if val == 'none' else val) for val in (self._configuration_arg('hardsub') or ['none'])]
        hardsub_langs = [lang for lang in available_formats if lang]
        if hardsub_langs and 'all' not in requested_hardsubs:
            full_format_langs = set(requested_hardsubs)
            self.to_screen(f'Available hardsub languages: {", ".join(hardsub_langs)}')
            self.to_screen(
                'To extract formats of a hardsub language, use '
                '"--extractor-args crunchyrollbeta:hardsub=<language_code or all>". '
                'See https://github.com/yt-dlp/yt-dlp#crunchyrollbeta-crunchyroll for more info',
                only_once=True)
        else:
            full_format_langs = set(map(str.lower, available_formats))

        audio_locale = traverse_obj(stream_response, ('audioLocale', {str}))
        hardsub_preference = qualities(requested_hardsubs[::-1])
        formats, subtitles = [], {}
        for format_id, hardsub_lang, stream_url in available_formats.values():
            if hardsub_lang.lower() in full_format_langs:
                adaptive_formats, dash_subs = self._extract_mpd_formats_and_subtitles(
                    stream_url, display_id, mpd_id=format_id, headers=CrunchyrollBaseIE._AUTH_HEADERS,
                    fatal=False, note=f'Downloading {f"{format_id} " if hardsub_lang else ""}MPD manifest')
                self._merge_subtitles(dash_subs, target=subtitles)
            else:
                continue  # XXX: Update this if meta mpd formats work; will be tricky with token invalidation
            for f in adaptive_formats:
                if f.get('acodec') != 'none':
                    f['language'] = audio_locale
                f['quality'] = hardsub_preference(hardsub_lang.lower())
            formats.extend(adaptive_formats)

        for locale, subtitle in traverse_obj(stream_response, (('subtitles', 'captions'), {dict.items}, ...)):
            subtitles.setdefault(locale, []).append(traverse_obj(subtitle, {'url': 'url', 'ext': 'format'}))

        # Invalidate stream token to avoid rate-limit
        error_msg = 'Unable to invalidate stream token; you may experience rate-limiting'
        if stream_token := stream_response.get('token'):
            self._request_webpage(Request(
                f'https://cr-play-service.prd.crunchyrollsvc.com/v1/token/{identifier}/{stream_token}/inactive',
                headers=headers, method='PATCH'), display_id, 'Invalidating stream token', error_msg, fatal=False)
        else:
            self.report_warning(error_msg)

        return formats, subtitles


class CrunchyrollCmsBaseIE(CrunchyrollBaseIE):
    _API_ENDPOINT = 'cms'
    _CMS_EXPIRY = None

    def _call_cms_api_signed(self, path, internal_id, lang, note='api'):
        if not CrunchyrollCmsBaseIE._CMS_EXPIRY or CrunchyrollCmsBaseIE._CMS_EXPIRY <= time_seconds():
            response = self._call_base_api('index/v2', None, lang, 'Retrieving signed policy')['cms_web']
            CrunchyrollCmsBaseIE._CMS_QUERY = {
                'Policy': response['policy'],
                'Signature': response['signature'],
                'Key-Pair-Id': response['key_pair_id'],
            }
            CrunchyrollCmsBaseIE._CMS_BUCKET = response['bucket']
            CrunchyrollCmsBaseIE._CMS_EXPIRY = parse_iso8601(response['expires']) - 10

        if not path.startswith('/cms/v2'):
            path = f'/cms/v2{CrunchyrollCmsBaseIE._CMS_BUCKET}/{path}'

        return self._call_base_api(
            path, internal_id, lang, f'Downloading {note} JSON (signed cms)', query=CrunchyrollCmsBaseIE._CMS_QUERY)


class CrunchyrollBetaIE(CrunchyrollCmsBaseIE):
    IE_NAME = 'crunchyroll'
    _VALID_URL = r'''(?x)
        https?://(?:beta\.|www\.)?crunchyroll\.com/
        (?:(?P<lang>\w{2}(?:-\w{2})?)/)?
        watch/(?!concert|musicvideo)(?P<id>\w+)'''
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
            'like_count': int,
            'dislike_count': int,
        },
        'params': {
            'skip_download': 'm3u8',
            'extractor_args': {'crunchyrollbeta': {'hardsub': ['de-DE']}},
            'format': 'bv[format_id~=hardsub]',
        },
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
            'like_count': int,
            'dislike_count': int,
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
            'like_count': int,
            'dislike_count': int,
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
        'skip': 'no longer exists',
    }, {
        'url': 'https://www.crunchyroll.com/watch/G62PEZ2E6',
        'info_dict': {
            'id': 'G62PEZ2E6',
            'description': 'md5:8d2f8b6b9dd77d87810882e7d2ee5608',
            'age_limit': 13,
            'duration': 65.138,
            'title': 'Garakowa -Restore the World-',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://www.crunchyroll.com/de/watch/GY2P1Q98Y',
        'only_matching': True,
    }, {
        'url': 'https://beta.crunchyroll.com/pt-br/watch/G8WUN8VKP/the-ruler-of-conspiracy',
        'only_matching': True,
    }]
    # We want to support lazy playlist filtering and movie listings cannot be inside a playlist
    _RETURN_TYPE = 'video'

    def _real_extract(self, url):
        lang, internal_id = self._match_valid_url(url).group('lang', 'id')

        # We need to use unsigned API call to allow ratings query string
        response = traverse_obj(self._call_api(
            f'objects/{internal_id}', internal_id, lang, 'object info', {'ratings': 'true'}), ('data', 0, {dict}))
        if not response:
            raise ExtractorError(f'No video with id {internal_id} could be found (possibly region locked?)', expected=True)

        object_type = response.get('type')
        if object_type == 'episode':
            result = self._transform_episode_response(response)

        elif object_type == 'movie':
            result = self._transform_movie_response(response)

        elif object_type == 'movie_listing':
            first_movie_id = traverse_obj(response, ('movie_listing_metadata', 'first_movie_id'))
            if not self._yes_playlist(internal_id, first_movie_id):
                return self.url_result(f'{self._BASE_URL}/{lang}watch/{first_movie_id}', CrunchyrollBetaIE, first_movie_id)

            def entries():
                movies = self._call_api(f'movie_listings/{internal_id}/movies', internal_id, lang, 'movie list')
                for movie_response in traverse_obj(movies, ('data', ...)):
                    yield self.url_result(
                        f'{self._BASE_URL}/{lang}watch/{movie_response["id"]}',
                        CrunchyrollBetaIE, **self._transform_movie_response(movie_response))

            return self.playlist_result(entries(), **self._transform_movie_response(response))

        else:
            raise ExtractorError(f'Unknown object type {object_type}')

        if not self._IS_PREMIUM and traverse_obj(response, (f'{object_type}_metadata', 'is_premium_only')):
            message = f'This {object_type} is for premium members only'
            if CrunchyrollBaseIE._REFRESH_TOKEN:
                self.raise_no_formats(message, expected=True, video_id=internal_id)
            else:
                self.raise_login_required(message, method='password', metadata_available=True)
        else:
            result['formats'], result['subtitles'] = self._extract_stream(internal_id)

        result['chapters'] = self._extract_chapters(internal_id)

        def calculate_count(item):
            return parse_count(''.join((item['displayed'], item.get('unit') or '')))

        result.update(traverse_obj(response, ('rating', {
            'like_count': ('up', {calculate_count}),
            'dislike_count': ('down', {calculate_count}),
        })))

        return result

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
                'season_number': ('season_number', ({int}, {float_or_none})),
                'episode_number': ('sequence_number', ({int}, {float_or_none})),
                'age_limit': ('maturity_ratings', -1, {parse_age_limit}),
                'language': ('audio_locale', {str}),
            }, get_all=False),
        }

    @staticmethod
    def _transform_movie_response(data):
        metadata = traverse_obj(data, (('movie_metadata', 'movie_listing_metadata', None), {dict}), get_all=False) or {}
        return {
            'id': data['id'],
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}, {lambda x: x.replace(r'\r\n', '\n')}),
                'thumbnails': ('images', 'thumbnail', ..., ..., {
                    'url': ('source', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }),
            }),
            **traverse_obj(metadata, {
                'duration': ('duration_ms', {lambda x: float_or_none(x, 1000)}),
                'age_limit': ('maturity_ratings', -1, {parse_age_limit}),
            }),
        }


class CrunchyrollBetaShowIE(CrunchyrollCmsBaseIE):
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
            seasons_response = self._call_cms_api_signed(f'seasons?series_id={internal_id}', internal_id, lang, 'seasons')
            for season in traverse_obj(seasons_response, ('items', ..., {dict})):
                episodes_response = self._call_cms_api_signed(
                    f'episodes?season_id={season["id"]}', season["id"], lang, 'episode list')
                for episode_response in traverse_obj(episodes_response, ('items', ..., {dict})):
                    yield self.url_result(
                        f'{self._BASE_URL}/{lang}watch/{episode_response["id"]}',
                        CrunchyrollBetaIE, **CrunchyrollBetaIE._transform_episode_response(episode_response))

        return self.playlist_result(
            entries(), internal_id,
            **traverse_obj(self._call_api(f'series/{internal_id}', internal_id, lang, 'series'), ('data', 0, {
                'title': ('title', {str}),
                'description': ('description', {lambda x: x.replace(r'\r\n', '\n')}),
                'age_limit': ('maturity_ratings', -1, {parse_age_limit}),
                'thumbnails': ('images', ..., ..., ..., {
                    'url': ('source', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                })
            })))


class CrunchyrollMusicIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll:music'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?crunchyroll\.com/
        (?P<lang>(?:\w{2}(?:-\w{2})?/)?)
        watch/(?P<type>concert|musicvideo)/(?P<id>\w+)'''
    _TESTS = [{
        'url': 'https://www.crunchyroll.com/de/watch/musicvideo/MV5B02C79',
        'info_dict': {
            'ext': 'mp4',
            'id': 'MV5B02C79',
            'display_id': 'egaono-hana',
            'title': 'Egaono Hana',
            'track': 'Egaono Hana',
            'artists': ['Goose house'],
            'thumbnail': r're:(?i)^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
            'genres': ['J-Pop'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.crunchyroll.com/watch/musicvideo/MV88BB7F2C',
        'info_dict': {
            'ext': 'mp4',
            'id': 'MV88BB7F2C',
            'display_id': 'crossing-field',
            'title': 'Crossing Field',
            'track': 'Crossing Field',
            'artists': ['LiSA'],
            'thumbnail': r're:(?i)^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
            'genres': ['Anime'],
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'no longer exists',
    }, {
        'url': 'https://www.crunchyroll.com/watch/concert/MC2E2AC135',
        'info_dict': {
            'ext': 'mp4',
            'id': 'MC2E2AC135',
            'display_id': 'live-is-smile-always-364joker-at-yokohama-arena',
            'title': 'LiVE is Smile Always-364+JOKER- at YOKOHAMA ARENA',
            'track': 'LiVE is Smile Always-364+JOKER- at YOKOHAMA ARENA',
            'artists': ['LiSA'],
            'thumbnail': r're:(?i)^https://www.crunchyroll.com/imgsrv/.*\.jpeg?$',
            'description': 'md5:747444e7e6300907b7a43f0a0503072e',
            'genres': ['J-Pop'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.crunchyroll.com/de/watch/musicvideo/MV5B02C79/egaono-hana',
        'only_matching': True,
    }, {
        'url': 'https://www.crunchyroll.com/watch/concert/MC2E2AC135/live-is-smile-always-364joker-at-yokohama-arena',
        'only_matching': True,
    }, {
        'url': 'https://www.crunchyroll.com/watch/musicvideo/MV88BB7F2C/crossing-field',
        'only_matching': True,
    }]
    _API_ENDPOINT = 'music'

    def _real_extract(self, url):
        lang, internal_id, object_type = self._match_valid_url(url).group('lang', 'id', 'type')
        path, name = {
            'concert': ('concerts', 'concert info'),
            'musicvideo': ('music_videos', 'music video info'),
        }[object_type]
        response = traverse_obj(self._call_api(f'{path}/{internal_id}', internal_id, lang, name), ('data', 0, {dict}))
        if not response:
            raise ExtractorError(f'No video with id {internal_id} could be found (possibly region locked?)', expected=True)

        result = self._transform_music_response(response)

        if not self._IS_PREMIUM and response.get('isPremiumOnly'):
            message = f'This {response.get("type") or "media"} is for premium members only'
            if CrunchyrollBaseIE._REFRESH_TOKEN:
                self.raise_no_formats(message, expected=True, video_id=internal_id)
            else:
                self.raise_login_required(message, method='password', metadata_available=True)
        else:
            result['formats'], _ = self._extract_stream(f'music/{internal_id}', internal_id)

        return result

    @staticmethod
    def _transform_music_response(data):
        return {
            'id': data['id'],
            **traverse_obj(data, {
                'display_id': 'slug',
                'title': 'title',
                'track': 'title',
                'artists': ('artist', 'name', all),
                'description': ('description', {str}, {lambda x: x.replace(r'\r\n', '\n') or None}),
                'thumbnails': ('images', ..., ..., {
                    'url': ('source', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }),
                'genres': ('genres', ..., 'displayValue'),
                'age_limit': ('maturity_ratings', -1, {parse_age_limit}),
            }),
        }


class CrunchyrollArtistIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll:artist'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?crunchyroll\.com/
        (?P<lang>(?:\w{2}(?:-\w{2})?/)?)
        artist/(?P<id>\w{10})'''
    _TESTS = [{
        'url': 'https://www.crunchyroll.com/artist/MA179CB50D',
        'info_dict': {
            'id': 'MA179CB50D',
            'title': 'LiSA',
            'genres': ['Anime', 'J-Pop', 'Rock'],
            'description': 'md5:16d87de61a55c3f7d6c454b73285938e',
        },
        'playlist_mincount': 83,
    }, {
        'url': 'https://www.crunchyroll.com/artist/MA179CB50D/lisa',
        'only_matching': True,
    }]
    _API_ENDPOINT = 'music'

    def _real_extract(self, url):
        lang, internal_id = self._match_valid_url(url).group('lang', 'id')
        response = traverse_obj(self._call_api(
            f'artists/{internal_id}', internal_id, lang, 'artist info'), ('data', 0))

        def entries():
            for attribute, path in [('concerts', 'concert'), ('videos', 'musicvideo')]:
                for internal_id in traverse_obj(response, (attribute, ...)):
                    yield self.url_result(f'{self._BASE_URL}/watch/{path}/{internal_id}', CrunchyrollMusicIE, internal_id)

        return self.playlist_result(entries(), **self._transform_artist_response(response))

    @staticmethod
    def _transform_artist_response(data):
        return {
            'id': data['id'],
            **traverse_obj(data, {
                'title': 'name',
                'description': ('description', {str}, {lambda x: x.replace(r'\r\n', '\n')}),
                'thumbnails': ('images', ..., ..., {
                    'url': ('source', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }),
                'genres': ('genres', ..., 'displayValue'),
            }),
        }
