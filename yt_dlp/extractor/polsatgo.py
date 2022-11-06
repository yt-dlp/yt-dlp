from uuid import uuid4
import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    url_or_none,
    ExtractorError,
)


class PolsatGoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?polsat(?:box)?go\.pl/.+/(?P<id>[0-9a-fA-F]+)(?:[/#?]|$)'
    _TESTS = [{
        'url': 'https://polsatgo.pl/wideo/seriale/swiat-wedlug-kiepskich/5024025/sezon-1/5024197/swiat-wedlug-kiepskich-odcinek-1/4208/ogladaj',
        'info_dict': {
            'id': '4208',
            'ext': 'mp4',
            'title': 'Świat według Kiepskich - Odcinek 1',
            'age_limit': 12,
            'subtitles': 'count:1',
        },
        'params': {
            'listsubtitles': True,
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
                'application': 'firefox',
                'build': 2170000,
                'deviceType': 'pc',
                'os': 'linux',
                'player': 'html',
                'portal': 'pg'
            },
        },
    }

    def _extract_formats(self, sources, video_id):
        for source in sources or []:
            if not source.get('id'):
                continue
            url = url_or_none(self._call_api(
                'drm', video_id, 'getPseudoLicense', {'sourceId': source['id']}).get('url'))
            if url:
                yield {
                    'url': url,
                    'height': int_or_none(try_get(source, lambda x: x['quality'][:-1]))
                }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        media = self._call_api('navigation', video_id, 'prePlayData')['mediaItem']

        formats = list(self._extract_formats(
            try_get(media, lambda x: x['playback']['mediaSources']), video_id))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': media['displayInfo']['title'],
            'formats': formats,
            'age_limit': int_or_none(media['displayInfo']['ageGroup']),
            'subtitles': self.extract_subtitles(video_id),
        }

    def _get_subtitles(self, video_id):
        subtitles = {}
        for subtitle in self._call_api('navigation', video_id, 'getMedia')['subtitles']:
            subtitles.setdefault(subtitle['name'], []).append({
                'url': subtitle['src'],
            })
        return subtitles

    def _call_api(self, endpoint, media_id, method, params=None):
        rand_uuid = str(uuid4())
        client_name = self._configuration_arg('player_client', default=['web'])[0]
        client = self._CLIENTS.get(client_name)
        if not client:
            raise ExtractorError(f'Unsupported player_client {client_name}', expected=True)

        res = self._download_json(
            f'https://{client["domain"]}/rpc/{endpoint}/', media_id,
            note=f'Downloading {method} JSON metadata as {client_name}',
            data=json.dumps({
                'method': method,
                'id': '2137',
                'jsonrpc': '2.0',
                'params': {
                    **(params or {}),
                    'mediaId': media_id,
                    'userAgentData': client['client'],
                    'deviceId': {
                        'type': 'other',
                        'value': rand_uuid,
                    },
                    'clientId': rand_uuid,
                    'cpid': 1,
                },
            }).encode('utf-8'),
            headers={'Content-type': 'application/json'})
        if not res.get('result'):
            if res['error']['code'] == 13404:
                raise ExtractorError('This video is either unavailable in your region or is DRM protected', expected=True)
            raise ExtractorError(f'Solorz said: {res["error"]["message"]} - {res["error"]["data"]["userMessage"]}')
        return res['result']
