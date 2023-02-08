import base64
import datetime
import hmac
import hashlib
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


class PolsatGoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?polsat(?:box)?go\.pl/.+/(?P<id>[0-9a-fA-F]+)(?:[/#?]|$)'
    _NETRC_MACHINE = 'polsatgo'
    _TESTS = [{
        'url': 'https://polsatgo.pl/wideo/seriale/swiat-wedlug-kiepskich/5024025/sezon-1/5024197/swiat-wedlug-kiepskich-odcinek-1/4208/ogladaj',
        'info_dict': {
            'id': '4208',
            'ext': 'mp4',
            'title': 'Świat według Kiepskich - Odcinek 1',
            'age_limit': 12,
            'subtitles': 'count:1',
        },
    }]

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
        'web_box': {
            'domain': 'b2c-www.redefine.pl',
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

    def _perform_login(self, username, password):
        clients = self._configuration_arg('player_client', default=['android'])
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

    def _real_extract(self, url):
        video_id = self._match_id(url)

        clients = self._configuration_arg('player_client', default=[
            'web', 'web_box'] if 'web_box' in self._SESSIONS else ['web'])

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
        for subtitle in traverse_obj(media, ('displayInfo', 'subtitles')):
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
