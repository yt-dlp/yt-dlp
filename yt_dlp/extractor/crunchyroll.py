import base64
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    format_field,
    join_nonempty,
    parse_iso8601,
    qualities,
    traverse_obj,
    try_get,
)


class CrunchyrollBaseIE(InfoExtractor):
    _LOGIN_URL = 'https://www.crunchyroll.com/welcome/login'
    _API_BASE = 'https://api.crunchyroll.com'
    _NETRC_MACHINE = 'crunchyroll'
    params = None

    @property
    def is_logged_in(self):
        return self._get_cookies(self._LOGIN_URL).get('etp_rt')

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
                'referer': self._LOGIN_URL
            })
        if upsell_response['code'] != 'ok':
            raise ExtractorError('Could not get session id')
        session_id = upsell_response['data']['session_id']

        login_response = self._download_json(
            f'{self._API_BASE}/login.1.json', None, 'Logging in',
            data=urllib.parse.urlencode({
                'account': username,
                'password': password,
                'session_id': session_id
            }).encode('ascii'))
        if login_response['code'] != 'ok':
            raise ExtractorError('Login failed. Server message: %s' % login_response['message'], expected=True)
        if not self.is_logged_in:
            raise ExtractorError('Login succeeded but did not set etp_rt cookie')

    def _get_embedded_json(self, webpage, display_id):
        initial_state = self._parse_json(self._search_regex(
            r'__INITIAL_STATE__\s*=\s*({.+?})\s*;', webpage, 'initial state'), display_id)
        app_config = self._parse_json(self._search_regex(
            r'__APP_CONFIG__\s*=\s*({.+?})\s*;', webpage, 'app config'), display_id)
        return initial_state, app_config

    def _get_params(self, lang):
        if not CrunchyrollBaseIE.params:
            if self._get_cookies(f'https://www.crunchyroll.com/{lang}').get('etp_rt'):
                grant_type, key = 'etp_rt_cookie', 'accountAuthClientId'
            else:
                grant_type, key = 'client_id', 'anonClientId'

            initial_state, app_config = self._get_embedded_json(self._download_webpage(
                f'https://www.crunchyroll.com/{lang}', None, note='Retrieving main page'), None)
            api_domain = app_config['cxApiParams']['apiDomain'].replace('beta.crunchyroll.com', 'www.crunchyroll.com')

            auth_response = self._download_json(
                f'{api_domain}/auth/v1/token', None, note=f'Authenticating with grant_type={grant_type}',
                headers={
                    'Authorization': 'Basic ' + str(base64.b64encode(('%s:' % app_config['cxApiParams'][key]).encode('ascii')), 'ascii')
                }, data=f'grant_type={grant_type}'.encode('ascii'))
            policy_response = self._download_json(
                f'{api_domain}/index/v2', None, note='Retrieving signed policy',
                headers={
                    'Authorization': auth_response['token_type'] + ' ' + auth_response['access_token']
                })
            cms = policy_response.get('cms_web')
            bucket = cms['bucket']
            params = {
                'Policy': cms['policy'],
                'Signature': cms['signature'],
                'Key-Pair-Id': cms['key_pair_id']
            }
            locale = traverse_obj(initial_state, ('localization', 'locale'))
            if locale:
                params['locale'] = locale
            CrunchyrollBaseIE.params = (api_domain, bucket, params)
        return CrunchyrollBaseIE.params

    def _get_url_parts(self, url):
        return self._match_valid_url(url).group('lang', 'id', 'display_id')


class CrunchyrollBetaIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll'
    _VALID_URL = r'''(?x)
        https?://(?:beta|www)\.crunchyroll\.com/
        (?P<lang>(?:\w{2}(?:-\w{2})?/)?)
        watch/(?P<id>\w+)
        (?:/(?P<display_id>[\w-]+))?/?(?:[?#]|$)'''
    _TESTS = [{
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
            'thumbnail': r're:^https://www.crunchyroll.com/imgsrv/.*\.jpeg$',
            'chapters': 'count:2',
        },
        'params': {'skip_download': 'm3u8', 'format': 'all[format_id~=hardsub]'},
    }, {
        'url': 'https://www.crunchyroll.com/watch/GYE5WKQGR',
        'info_dict': {
            'id': 'GYE5WKQGR',
            'ext': 'mp4',
            'duration': 366.459,
            'timestamp': 1476788400,
            'description': 'md5:74b67283ffddd75f6e224ca7dc031e76',
            'title': 'SHELTER Episode  – Porter Robinson presents Shelter the Animation',
            'upload_date': '20161018',
            'series': 'SHELTER',
            'series_id': 'GYGG09WWY',
            'season': 'SHELTER',
            'season_id': 'GR09MGK4R',
            'season_number': 1,
            'episode': 'Porter Robinson presents Shelter the Animation',
            'episode_number': 0,
            'thumbnail': r're:^https://www.crunchyroll.com/imgsrv/.*\.jpeg$',
            'chapters': 'count:0',
        },
        'params': {'skip_download': True},
        'skip': 'Video is Premium only',
    }, {
        'url': 'https://www.crunchyroll.com/watch/GY2P1Q98Y',
        'only_matching': True,
    }, {
        'url': 'https://beta.crunchyroll.com/pt-br/watch/G8WUN8VKP/the-ruler-of-conspiracy',
        'only_matching': True,
    }]

    def _fetch_episode_and_stream_response(self, lang, internal_id, display_id, skip_if_inaccessible=False):
        api_domain, bucket, params = self._get_params(lang)

        # Fetch episode data
        episode_response = self._download_json(
            f'{api_domain}/cms/v2{bucket}/episodes/{internal_id}', display_id,
            note='Retrieving episode metadata', query=params)
        if episode_response.get('is_premium_only') and not bucket.endswith('crunchyroll'):
            if skip_if_inaccessible:
                return None
            if self.is_logged_in:
                raise ExtractorError('This video is for premium members only', expected=True)
            else:
                self.raise_login_required('This video is for premium members only')

        # Fetch stream data
        stream_response = self._download_json(
            f'{api_domain}{episode_response["__links__"]["streams"]["href"]}', display_id,
            note='Retrieving stream info', query=params)
        return episode_response, stream_response

    def _expand_responses_for_requested_langs(self, requested_langs, lang, internal_id, display_id, versions):
        _, stream_response_to_expand = versions[internal_id]
        stream_versions = traverse_obj(stream_response_to_expand, 'versions') or []
        for version in stream_versions:
            audio_lang = (version.get('audio_locale') or 'unknown').lower()
            if requested_langs and audio_lang not in requested_langs:
                continue
            version_id = version.get('guid')
            if not version_id or version_id in versions:
                continue
            # Fetch responses for current version (will be a different page).
            responses = self._fetch_episode_and_stream_response(lang, version_id, display_id, skip_if_inaccessible=True)
            if not responses:
                continue
            versions[version_id] = responses

    def _real_extract(self, url):
        # Split URL into its parts.
        lang, internal_id, display_id = self._get_url_parts(url)

        # Check what formats were requested.
        requested_hardsubs = [('' if val == 'none' else val) for val in (self._configuration_arg('hardsub') or ['none'])]
        hardsub_preference = qualities(requested_hardsubs[::-1])
        requested_formats = self._configuration_arg('format') or ['adaptive_hls']
        requested_langs = self._configuration_arg('language', casesense=False) or ['default']

        # Fetch default version given by the URL.
        # Every version is represented by a different page. When switching to a different
        # audio language in the crunchyroll player the URL of the page changes to a different ID.
        # Hint: Each value in the 'versions' dict consists of a tuple containing
        # an 'episode_response' and a 'stream_response'
        # -> {"some_id": (episode_response_dict, stream_response_dict)}.
        versions = {
            # Fetch requested version.
            internal_id: self._fetch_episode_and_stream_response(lang, internal_id, display_id)
        }

        # Parse requested_langs.
        # Specifying the 'language' option can significantly slow down the extraction process,
        # but formats for different languages will be found as a result.
        # Set 'all' to extract all versions (All other keys will be ignored if 'all' is set).
        # Use the language key 'default' to specify whether the URL`s language version,
        # should be kept alongside the other requested languages.
        # Use the language key 'unknown' to specify whether unknown language versions
        # should be kept alongside the other requested languages.
        # e.g. requested_langs = ['default', 'ja-JP', 'unknown']
        # -> Would keep the URL`s language, plus Japanese and unknown languages.
        # Also, the code will behave like the previous version of the extractor,
        # if 'language' is not set or is set to only ['default'].
        if ['default'] == requested_langs:
            requested_langs = None
        elif 'all' in requested_langs:
            requested_langs = []
        else:
            # Replace all 'default' keys with the default audio language.
            _, default_stream_response = versions[internal_id]
            default_audio_lang = (default_stream_response.get('audio_locale') or '').lower()
            requested_langs = [(default_audio_lang if val == 'default' else val) for val in requested_langs]

        # Collect different audio versions.
        if requested_langs is not None:
            # Include requested languages versions if available.
            self._expand_responses_for_requested_langs(requested_langs, lang, internal_id, display_id, versions)

        # Fields to fill with data while iterating through all versions.
        formats = []
        subtitles = {}

        # Iterate through versions and collect all formats and subtitles.
        for version_id, responses in versions.items():
            episode_response, stream_response = responses
            # Skip version, if audio lang is not in requested_langs.
            audio_lang = (stream_response.get('audio_locale') or '').lower()
            if requested_langs and audio_lang not in requested_langs:
                continue

            # Lambda to get values of key from stream_response.
            get_streams = lambda name: (traverse_obj(stream_response, name) or {}).items()

            # 1. Find all available formats for current version.
            available_formats = {}
            for stream_type, streams in get_streams('streams'):
                if stream_type not in requested_formats:
                    continue
                for stream in streams.values():
                    if not stream.get('url'):
                        continue
                    hardsub_lang = stream.get('hardsub_locale') or ''
                    format_id = join_nonempty(stream_type, format_field(stream, 'hardsub_locale', 'hardsub-%s'))
                    available_formats[hardsub_lang] = (stream_type, format_id, hardsub_lang, stream['url'])
            if '' in available_formats and 'all' not in requested_hardsubs:
                full_format_langs = set(requested_hardsubs)
                self.to_screen(
                    'To get all formats of a hardsub language, use '
                    '"--extractor-args crunchyrollbeta:hardsub=<language_code or all>". '
                    'See https://github.com/yt-dlp/yt-dlp#crunchyrollbeta-crunchyroll for more info',
                    only_once=True)
            else:
                full_format_langs = set(map(str.lower, available_formats))

            # 2. Expand formats with multiple resolutions and add them to 'formats' dict.
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
                        f['language'] = audio_lang
                    f['quality'] = hardsub_preference(hardsub_lang.lower())
                    # If multiple versions are available, add episode options to each format, as fields
                    # such as 'title', 'season' or 'season_id' may be different for each version.
                    # e.g. if a version is selected that is not the one specified by the user,
                    # the 'season_id' would most likely be incorrect. (the selected format will
                    # override the 'default version values')
                    if len(versions) > 1:
                        f.update(self._get_episode_options(version_id, episode_response))
                formats.extend(adaptive_formats)

            # 3. Add subtitles of current version to 'subtitle' dict.
            subtitles.update({
                lang: [{
                    'url': subtitle_data.get('url'),
                    'ext': subtitle_data.get('format')
                }] for lang, subtitle_data in get_streams('subtitles')
            })

        # Find chapters.
        chapters = None
        # If no intro chapter is available, a 403 without usable data is returned.
        intro_chapter = self._download_json(f'https://static.crunchyroll.com/datalab-intro-v2/{internal_id}.json',
                                            display_id, fatal=False, errnote=False)
        if isinstance(intro_chapter, dict):
            chapters = [{
                'title': 'Intro',
                'start_time': float_or_none(intro_chapter.get('startTime')),
                'end_time': float_or_none(intro_chapter.get('endTime'))
            }]

        # Build extracted data dict from default version.
        episode_response, _ = versions[internal_id]
        options = {
            'formats': formats,
            'subtitles': subtitles,
            'chapters': chapters,
            'thumbnails': [{
                'url': thumb.get('source'),
                'width': thumb.get('width'),
                'height': thumb.get('height'),
            } for thumb in traverse_obj(episode_response, ('images', 'thumbnail', ..., ...)) or []],
        }
        # Add the 'default version values'.
        # They may be overwritten, if a different version is applied / selected by the user.
        options.update(self._get_episode_options(internal_id, episode_response))
        # Return extracted data dict
        return options

    @staticmethod
    def _get_episode_options(internal_id, episode_response):
        return {
            'id': internal_id,
            'title': '%s Episode %s – %s' % (
                episode_response.get('season_title'), episode_response.get('episode'), episode_response.get('title')),
            'description': try_get(episode_response, lambda x: x['description'].replace(r'\r\n', '\n')),
            'duration': float_or_none(episode_response.get('duration_ms'), 1000),
            'timestamp': parse_iso8601(episode_response.get('upload_date')),
            'series': episode_response.get('series_title'),
            'series_id': episode_response.get('series_id'),
            'season': episode_response.get('season_title'),
            'season_id': episode_response.get('season_id'),
            'season_number': episode_response.get('season_number'),
            'episode': episode_response.get('title'),
            'episode_number': episode_response.get('sequence_number'),
        }


class CrunchyrollBetaShowIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll:playlist'
    _VALID_URL = r'''(?x)
        https?://(?:beta|www)\.crunchyroll\.com/
        (?P<lang>(?:\w{2}(?:-\w{2})?/)?)
        series/(?P<id>\w+)
        (?:/(?P<display_id>[\w-]+))?/?(?:[?#]|$)'''
    _TESTS = [{
        'url': 'https://www.crunchyroll.com/series/GY19NQ2QR/Girl-Friend-BETA',
        'info_dict': {
            'id': 'GY19NQ2QR',
            'title': 'Girl Friend BETA',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://beta.crunchyroll.com/it/series/GY19NQ2QR',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, internal_id, display_id = self._get_url_parts(url)
        api_domain, bucket, params = self._get_params(lang)

        series_response = self._download_json(
            f'{api_domain}/cms/v2{bucket}/series/{internal_id}', display_id,
            note='Retrieving series metadata', query=params)

        seasons_response = self._download_json(
            f'{api_domain}/cms/v2{bucket}/seasons?series_id={internal_id}', display_id,
            note='Retrieving season list', query=params)

        def entries():
            for season in seasons_response['items']:
                episodes_response = self._download_json(
                    f'{api_domain}/cms/v2{bucket}/episodes?season_id={season["id"]}', display_id,
                    note=f'Retrieving episode list for {season.get("slug_title")}', query=params)
                for episode in episodes_response['items']:
                    episode_id = episode['id']
                    episode_display_id = episode['slug_title']
                    yield {
                        '_type': 'url',
                        'url': f'https://www.crunchyroll.com/{lang}watch/{episode_id}/{episode_display_id}',
                        'ie_key': CrunchyrollBetaIE.ie_key(),
                        'id': episode_id,
                        'title': '%s Episode %s – %s' % (episode.get('season_title'), episode.get('episode'), episode.get('title')),
                        'description': try_get(episode, lambda x: x['description'].replace(r'\r\n', '\n')),
                        'duration': float_or_none(episode.get('duration_ms'), 1000),
                        'series': episode.get('series_title'),
                        'series_id': episode.get('series_id'),
                        'season': episode.get('season_title'),
                        'season_id': episode.get('season_id'),
                        'season_number': episode.get('season_number'),
                        'episode': episode.get('title'),
                        'episode_number': episode.get('sequence_number'),
                        'language': episode.get('audio_locale'),
                    }

        return self.playlist_result(entries(), internal_id, series_response.get('title'))
