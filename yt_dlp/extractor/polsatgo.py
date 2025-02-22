import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
    url_or_none,
)


class PolsatGoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?polsat(?:box)?go\.pl/.+/(?P<id>[0-9a-fA-F]+)(?:[/#?]|$)'
    _TESTS = [{
        'url': 'https://polsatgo.pl/wideo/seriale/swiat-wedlug-kiepskich/5024045/sezon-1/5028300/swiat-wedlug-kiepskich-odcinek-88/4121',
        'info_dict': {
            'id': '4121',
            'ext': 'mp4',
            'title': 'Świat według Kiepskich - Odcinek 88',
            'age_limit': 12,
        },
    }]

    def _extract_formats(self, sources, video_id):
        for source in sources or []:
            if not source.get('id'):
                continue
            url = url_or_none(self._call_api(
                'drm', video_id, 'getPseudoLicense',
                {'mediaId': video_id, 'sourceId': source['id']}).get('url'))
            if not url:
                continue
            yield {
                'url': url,
                'height': int_or_none(try_get(source, lambda x: x['quality'][:-1])),
            }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        media = self._call_api('navigation', video_id, 'prePlayData', {'mediaId': video_id})['mediaItem']

        formats = list(self._extract_formats(
            try_get(media, lambda x: x['playback']['mediaSources']), video_id))

        return {
            'id': video_id,
            'title': media['displayInfo']['title'],
            'formats': formats,
            'age_limit': int_or_none(media['displayInfo']['ageGroup']),
        }

    def _call_api(self, endpoint, media_id, method, params):
        rand_uuid = str(uuid.uuid4())
        res = self._download_json(
            f'https://b2c-mobile.redefine.pl/rpc/{endpoint}/', media_id,
            note=f'Downloading {method} JSON metadata',
            data=json.dumps({
                'method': method,
                'id': '2137',
                'jsonrpc': '2.0',
                'params': {
                    **params,
                    'userAgentData': {
                        'deviceType': 'mobile',
                        'application': 'native',
                        'os': 'android',
                        'build': 10003,
                        'widevine': False,
                        'portal': 'pg',
                        'player': 'cpplayer',
                    },
                    'deviceId': {
                        'type': 'other',
                        'value': rand_uuid,
                    },
                    'clientId': rand_uuid,
                    'cpid': 1,
                },
            }).encode(),
            headers={'Content-type': 'application/json'})
        if not res.get('result'):
            if res['error']['code'] == 13404:
                raise ExtractorError('This video is either unavailable in your region or is DRM protected', expected=True)
            raise ExtractorError(f'Solorz said: {res["error"]["message"]} - {res["error"]["data"]["userMessage"]}')
        return res['result']
