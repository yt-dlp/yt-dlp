import json
import time

from .wrestleuniverse import WrestleUniverseBaseIE
from ..utils import (
    ExtractorError,
    clean_html,
    parse_iso8601,
    parse_qs,
    update_url,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class SPWNIE(WrestleUniverseBaseIE):
    _BASE_URL = 'https://spwn.jp'
    _LOGIN_HEADERS = {'Content-Type': 'application/json'}
    _LOGIN_HINT = (
        'Use --username refresh --password <refreshToken>, --username and --password, '
        '--netrc-cmd, or --netrc (spwn) to provide account credentials')
    _LOGIN_QUERY = {'key': 'AIzaSyC-RDWv-QnYNWsJ6geLPpFYArlo2uPWCpA'}
    _NETRC_MACHINE = 'spwn'
    _VALID_URL = r'https?://spwn\.jp/events/(?P<id>[^/?#]+)(/streaming)?'
    _TESTS = [{
        'url': 'https://spwn.jp/events/evt_wG62Svb4HkCQkK3QwDqI/streaming?vid=ki6OfjHeVlDGVKtEJwe4',
        'info_dict': {
            'id': 'ki6OfjHeVlDGVKtEJwe4',
            'ext': 'mp4',
            'title': '本編',
            'categories': 'count:1',
            'description': 'md5:7b6ef6bc591dc3e8641acf224a2345fe',
            'release_date': '20250606',
            'release_timestamp': 1749200400,
            'series': '劇場版「ポールプリンセス!!」【劇場版アニメ本編配信】',
            'series_id': 'evt_wG62Svb4HkCQkK3QwDqI',
            'tags': 'count:2',
            'thumbnail': r're:https?://public-web\.spwn\.jp/events/.+',
            'timestamp': 1749200400,
            'upload_date': '20250606',
        },
        'skip': 'Paid only',
    }, {
        'url': 'https://spwn.jp/events/evt_wG62Svb4HkCQkK3QwDqI',
        'info_dict': {
            'id': 'evt_wG62Svb4HkCQkK3QwDqI',
            'title': '劇場版「ポールプリンセス!!」【劇場版アニメ本編配信】',
        },
        'playlist_count': 2,
        'skip': 'Paid only',
    }]

    @WrestleUniverseBaseIE._TOKEN.getter
    def _TOKEN(self):
        if not self._REAL_TOKEN or self._TOKEN_EXPIRY <= int(time.time()):
            if not self._REFRESH_TOKEN:
                self.raise_login_required(
                    f'No refreshToken provided. {self._LOGIN_HINT}', method=None)
            self._refresh_token()
        return self._REAL_TOKEN

    def _perform_login(self, username, password):
        if username.lower() == 'refresh':
            self._REFRESH_TOKEN = password
            return self._refresh_token()
        return super()._perform_login(username, password)

    def _call_api(self, event_id, note, url=None, path=None):
        if not url:
            url = f'https://firestore.googleapis.com/v1/projects/spwn-balus/databases/(default)/documents/{path}'

        return traverse_obj(self._download_json(
            url, event_id, f'Downloading {note}', fatal=False,
        ), ('fields', {dict}), default={})

    def _real_extract(self, url):
        event_id = self._match_id(url)
        event = self._call_api(event_id, 'event info', path=f'events/{event_id}')
        info = self._download_json(
            'https://us-central1-spwn-balus.cloudfunctions.net/getStreamingKey/',
            event_id, headers={
                'Authorization': f'Bearer {self._TOKEN}',
                'Content-Type': 'application/json',
                'Origin': self._BASE_URL,
            }, data=json.dumps({'eid': event_id}).encode())
        if traverse_obj(info, ('isError', {bool})):
            msg = traverse_obj(info, ('msg', {str}, filter))
            raise ExtractorError(
                msg or 'API returned an error response', expected=bool(msg))

        video_id = traverse_obj(parse_qs(url), ('vid', 0, {str}))
        if not video_id:
            return self.playlist_result([self.url_result(
                f'{self._BASE_URL}/events/{event_id}/streaming?vid={vid}', SPWNIE,
            ) for vid in traverse_obj(info, ('videoIds', ..., {str}, filter))],
                event_id, traverse_obj(event, ('title', 'stringValue', {str})))

        video = self._call_api(event_id, 'video info', path=f'streaming/{event_id}/videos/{video_id}')
        policy, signature, m3u8_url = traverse_obj(info, ('cookies', video_id, 'default', (
            ('cookie', 'CloudFront-Policy', {str}, {require('CloudFront policy')}),
            ('cookie', 'CloudFront-Signature', {str}, {require('CloudFront signature')}),
            ('url', {url_or_none}, {require('manifest URL')}),
        )))

        return {
            'id': video_id,
            'title': traverse_obj(video, ('name', 'stringValue', {str})),
            'formats': self._extract_m3u8_formats(
                update_url(m3u8_url, netloc='vod.spwnlive.net'), video_id,
                'mp4', query={'policy': policy, 'signature': signature}),
            'series_id': event_id,
            **traverse_obj(event, {
                'cast': ('artistRefs', 'arrayValue', 'values', ..., 'referenceValue',
                         {lambda x: self._call_api(event_id, 'artist info', url=f'{self._API_BASE}/{x}')},
                         'name', 'stringValue', {str}, filter, all, filter),
                'categories': ('categories', 'arrayValue', 'values', ..., 'stringValue', {str}, filter, all, filter),
                'description': ('description', 'stringValue', {clean_html}, {clean_html}, filter),
                'series': ('title', 'stringValue', {str}),
                'tags': ('twitterHashTag', 'arrayValue', 'values', ..., 'stringValue', {str}, filter, all, filter),
                'thumbnail': ('defaultImg', 'stringValue', {url_or_none}),
            }),
            **traverse_obj(event, ('parts', 'arrayValue', 'values', ..., 'mapValue', 'fields', {
                'release_timestamp': ('openTime', 'timestampValue', {parse_iso8601}),
                'timestamp': ('startTime', 'timestampValue', {parse_iso8601}),
            }, any)),
        }
