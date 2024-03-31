import base64
import datetime
import hmac
import hashlib
import itertools
import json
from urllib.request import unquote
from uuid import uuid4

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    url_or_none,
    traverse_obj,
    ExtractorError,
)


class PolsatGoBaseExtractor(InfoExtractor):
    def _real_initialize(self):
        for client_name in self._configuration_arg('player_client', default=self._CLIENTS.keys()):
            client = self._CLIENTS[client_name]

            if not client.get('cookie_domain'):
                continue

            portal_cookies = [cookie for cookie in self.cookiejar
                              if cookie.domain == client['cookie_domain']]

            def get_cookie(name):
                return next((
                    self._parse_json(cookie.value, None, unquote)
                    for cookie in portal_cookies if cookie.name == name), {})

            user_session = get_cookie('user-session')
            user_recognition = get_cookie('user-recognition')

            if user_session and user_recognition:
                self._SESSIONS[client_name] = {
                    'user_session': user_session,
                    'user_recognition': user_recognition,
                }

    def _call_api(self, endpoint, media_id, method, params=None, client_name='web', fatal=True, device_id=None, client_id=None):
        client = self._CLIENTS.get(client_name)
        if not client:
            raise ExtractorError(f'Unsupported player_client {client_name}', expected=True)
        session = self._SESSIONS.get(client_name, {})
        user_session = session.get('user_session') or {}
        user_recognition = session.get('user_recognition') or {}

        auth_params = {}
        if user_session:
            if user_session['keyExpirationTime'] < datetime.datetime.now().timestamp():
                self.report_warning(f'User session for {client_name} expired, trying anyway')

            unsigned = '|'.join((user_session['id'], str(user_session['keyExpirationTime']), endpoint, method))
            mac = hmac.new(base64.urlsafe_b64decode(user_session['key']), unsigned.encode('utf-8'), hashlib.sha256)
            auth_params.setdefault('authData', {})['sessionToken'] = unsigned + '|' + base64.urlsafe_b64encode(mac.digest()).decode('utf-8')

        res = self._download_json(
            f'https://{client["domain"]}/rpc/{endpoint}/', media_id,
            note=f'Downloading {method} JSON metadata as {client_name}',
            data=json.dumps({
                'method': method,
                'id': 1,
                'jsonrpc': '2.0',
                'params': {
                    **(params or {}),
                    **auth_params,
                    'mediaId': media_id,
                    'userAgentData': client['client'],
                    'deviceId': {
                        'type': 'other',
                        'value': user_recognition.get('deviceId') or device_id or str(uuid4()),
                    },
                    'clientId': user_recognition.get('clientId') or client_id or str(uuid4()),
                    'cpid': 1,
                },
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json'})
        if not res.get('result'):
            if not fatal:
                return None
            if res['error']['code'] == 13404:
                raise ExtractorError('This video is either unavailable in your region or is DRM protected', expected=True)
            raise ExtractorError(f'Solorz said: {res["error"]["message"]} - {res["error"]["data"]["userMessage"]}')
        return res['result']

    def _perform_login(self, username, password):
        clients = self._configuration_arg('player_client', default=self._CLIENTS.keys())
        for client_name in clients:
            if client_name in self._SESSIONS:
                continue
            client_id = str(uuid4())
            device_id = str(uuid4())
            response = self._call_api('auth/login', None, 'login', {
                'authData': {
                    'deviceId': {
                        'type': 'other',
                        'value': device_id,
                    },
                    'login': username,
                    'password': password,
                },
            }, client_name=client_name, device_id=device_id, client_id=client_id)
            self._SESSIONS[client_name] = {
                'user_session': response['session'],
                'user_recognition': {
                    'clientId': client_id,
                    'deviceId': device_id,
                },
            }


class PolsatGoBaseVideoExtractor(PolsatGoBaseExtractor):
    def _extract_formats(self, sources, video_id, client_name='web'):
        for source in sources or []:
            if not source.get('id'):
                continue
            url = url_or_none((self._call_api(
                'drm', video_id, 'getPseudoLicense', {'sourceId': source['id']},
                client_name=client_name, fatal=False) or {}).get('url'))
            if url:
                yield {
                    'url': url,
                    'height': int_or_none(try_get(source, lambda x: x['quality'][:-1])),
                    'format_note': f'{source["quality"]}, {client_name}',
                }

    def _extract_video(self, video_id):
        clients = self._configuration_arg('player_client', default=self._CLIENTS.keys())

        all_medias = [(client, self._call_api('navigation', video_id, 'prePlayData',
                                              client_name=client, fatal=False))
                      for client in clients]
        all_medias = [(n, m) for n, m in all_medias if traverse_obj(
            m, ('mediaItem', 'displayInfo', 'title'),
            get_all=False) not in ('Materiał z ograniczonym dostępem', None)]
        media = next((m['mediaItem'] for _, m in all_medias), None)
        if media is None:
            raise ExtractorError('None of the clients returned valid mediaItem')

        format_lists = [self._extract_formats(
            traverse_obj(media_, ('mediaItem', 'playback', 'mediaSources'), default=[]),
            video_id, client_name=client) for client, media_ in all_medias
        ]
        formats = []
        for fmts in format_lists:
            formats.extend(fmts)

        subtitles = {}
        for subtitle in traverse_obj(media, ('displayInfo', 'subtitles'), default=()):
            subtitles.setdefault(subtitle['name'], []).append({
                'url': subtitle['src'],
                'ext': subtitle.get('format'),
            })

        return {
            'id': video_id,
            'title': media['displayInfo']['title'],
            'formats': formats,
            'age_limit': int_or_none(media['displayInfo']['ageGroup']),
            'subtitles': subtitles,
        }


class PolsatGoPlatformBaseExtractor(InfoExtractor):
    _NETRC_MACHINE = 'polsatgo'
    _CLIENTS = {
        'android': {
            'domain': 'b2c-mobile.redefine.pl',
            'client': {
                'deviceType': 'mobile',
                'application': 'native',
                'os': 'android',
                'build': 10003,
                'widevine': False,
                'portal': 'pg',
                'player': 'cpplayer',
            },
        },
        'web': {
            'domain': 'b2c.redefine.pl',
            'client': {
                'application': 'chrome',
                'build': 1,
                'deviceType': 'pc',
                'os': 'windows',
                'player': 'html',
                'portal': 'pg',
            },
            'cookie_domain': '.polsatgo.pl',
        },
    }
    _SESSIONS = {}


class PolsatBoxGoPlatformBaseExtractor(InfoExtractor):
    _NETRC_MACHINE = 'polsatboxgo'
    _CLIENTS = {
        'web': {
            'domain': 'b2c.redefine.pl',
            'client': {
                'application': 'chrome',
                'build': 1,
                'deviceType': 'pc',
                'os': 'windows',
                'player': 'html',
                'portal': 'pbg',
            },
            'cookie_domain': '.polsatboxgo.pl',
        },
    }
    _SESSIONS = {}

    def _force_use_pg_for_video(self):
        return 'video' in self._configuration_arg('force_use_pg', default=[], ie_key=PolsatBoxGoIE)

    def _force_use_pg_for_series(self):
        return 'series' in self._configuration_arg('force_use_pg', default=[], ie_key=PolsatBoxGoIE)


class PolsatGoIE(PolsatGoBaseVideoExtractor, PolsatGoPlatformBaseExtractor):
    _VALID_URL = r'(?:polsatgo:|https?://(?:www\.)?polsatgo\.pl/wideo/(?:film/|(?:programy|seriale)/[^/]+/\d+/(?:[^/]+/\d+/)?)[^/]+/)(?P<id>[a-f\d]+)'
    _TESTS = [{
        'url': 'https://polsatgo.pl/wideo/seriale/swiat-wedlug-kiepskich/5024025/sezon-1/5024197/swiat-wedlug-kiepskich-odcinek-1/4208/ogladaj',
        'info_dict': {
            'id': '4208',
            'ext': 'mp4',
            'title': 'Świat według Kiepskich - Odcinek 1',
            'age_limit': 12,
            'subtitles': 'count:1',
        },
    }, {
        'url': 'https://polsatgo.pl/wideo/seriale/rodzina-zastepcza/5024220/rodzina-zastepcza-odcinek-1/7928',
        'info_dict': {
            'id': '7928',
            'ext': 'mp4',
            'title': 'Rodzina Zastępcza - Odcinek 1',
            'age_limit': 0,
            'subtitles': 'count:0',
        },
    }, {
        'url': 'https://polsatgo.pl/wideo/programy/gry-komputerowe-show/5027365/wywiad/5027366/gry-komputerowe-show-wywiad-odcinek-10/b7768cca8a0f9cabd68f4be4cd809988',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._extract_video(video_id)


class PolsatBoxGoIE(PolsatGoBaseVideoExtractor, PolsatBoxGoPlatformBaseExtractor):
    _VALID_URL = r'(?:polsatboxgo:|https?://(?:www\.)?polsatboxgo\.pl/wideo/(?:film/|(?:programy|seriale)/[^/]+/\d+/(?:[^/]+/\d+/)?)[^/]+/)(?P<id>[a-f\d]+)'
    _NETRC_MACHINE = 'polsatboxgo'
    _TESTS = [{
        # should fallback to Polsat Go if no session
        'url': 'https://polsatboxgo.pl/wideo/programy/gry-komputerowe-show/5027365/wywiad/5027366/gry-komputerowe-show-wywiad-odcinek-10/b7768cca8a0f9cabd68f4be4cd809988',
        'info_dict': {
            'id': 'b7768cca8a0f9cabd68f4be4cd809988',
            'ext': 'mp4',
            'title': 'Gry Komputerowe Show: Wywiad - Odcinek 10',
            'age_limit': 0,
        },
        'expected_warnings': ['no PBG session'],
    }, {
        'url': 'https://polsatboxgo.pl/wideo/film/sprawiedliwi-wydzial-kryminalny-wszystko-sie-moze-zdarzyc/189062750c1ce3e2971c7a331c825825',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        clients = self._configuration_arg('player_client', default=self._CLIENTS.keys())

        if self._force_use_pg_for_video():
            return self.url_result(f'polsatgo:{video_id}', ie=PolsatGoIE)

        if not any((client in self._SESSIONS for client in clients)):
            self.report_warning('Polsat Box Go url provided, but no PBG session or credentials available, extracting as Polsat Go instead')
            return self.url_result(f'polsatgo:{video_id}', ie=PolsatGoIE)

        return self._extract_video(video_id)


class PolsatGoBaseCategoryExtractor(PolsatGoBaseExtractor):
    _PAGE_SIZE = 50

    def _get_category_page(self, category_id, offset=0, limit=None, client_name='web'):
        return self._call_api('navigation', category_id, 'getCategoryContent', {
            'catid': category_id,
            'offset': offset,
            'limit': limit,
        }, client_name=client_name)['results']

    def _category_episode(self, episode):
        return {
            '_type': 'url',
            'id': episode['id'],
            'url': f'{self._NETRC_MACHINE}:{episode["id"]}',
            'title': episode.get('title'),
            'description': episode.get('description'),
        }

    def _category_entries(self, category_id, client_name='web'):
        for offset in itertools.count(0, self._PAGE_SIZE):
            page_content = self._get_category_page(category_id, offset=offset, limit=self._PAGE_SIZE,
                                                   client_name=client_name)

            if not page_content:
                break
            yield from (self._category_episode(episode) for episode in page_content)

    def _category_extract(self, category_id, client_name='web'):
        category_int = int(category_id)
        meta = self._call_api('navigation', category_id, 'getCategory', {
            'catid': category_int,
        }, client_name=client_name)

        return {
            '_type': 'playlist',
            'id': category_id,
            'title': meta['name'],
            'description': meta.get('description'),
            'entries': self._category_entries(category_int, client_name=client_name),
        }


class PolsatGoCategoryIE(PolsatGoBaseCategoryExtractor, PolsatGoPlatformBaseExtractor):
    _VALID_URL = r'(?:polsatgocat:|https?://(?:www\.)?polsatgo\.pl/wideo/[^/]+/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://polsatgo.pl/wideo/rodzina-zastepcza/5024220/autoplay',
        'info_dict': {
            'id': '5024220',
            'title': 'Rodzina Zastępcza',
            'description': 'md5:175e5653b4794a0f0ee092dfbbedc27d',
        },
        'playlist_count': 333,
    }]

    def _real_extract(self, url):
        category_id = self._match_id(url)

        return self._category_extract(category_id)


class PolsatBoxGoCategoryIE(PolsatGoBaseCategoryExtractor, PolsatBoxGoPlatformBaseExtractor):
    _VALID_URL = r'(?:polsatboxgocat:|https?://(?:www\.)?polsatboxgo\.pl/wideo/[^/]+/)(?P<id>\d+)'
    _TESTS = [{
        # category only extractable as pbg even though entries work with pg
        'url': 'https://polsatboxgo.pl/wideo/gry-komputerowe-show/5027365/autoplay',
        'info_dict': {
            'id': '5027365',
            'title': 'Gry Komputerowe Show',
            'description': 'md5:63c508956f22a0fd5421068feadd7823',
        },
        'playlist_mincount': 18,
    }]

    def _real_extract(self, url):
        category_id = self._match_id(url)

        if self._force_use_pg_for_series():
            return self.url_result(f'polsatgocat:{category_id}', ie=PolsatGoCategoryIE)

        return self._category_extract(category_id)
