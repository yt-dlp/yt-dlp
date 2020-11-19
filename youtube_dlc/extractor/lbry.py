# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    mimetype2ext,
    try_get,
)


class LBRYIE(InfoExtractor):
    IE_NAME = 'lbry.tv'
    _VALID_URL = r'https?://(?:www\.)?(?:lbry\.tv|odysee\.com)/(?P<id>@[0-9a-zA-Z-]+:[0-9a-z]+/[0-9a-zA-Z().-]+:[0-9a-z])'
    _TESTS = [{
        # Video
        'url': 'https://lbry.tv/@Mantega:1/First-day-LBRY:1',
        'md5': '65bd7ec1f6744ada55da8e4c48a2edf9',
        'info_dict': {
            'id': '17f983b61f53091fb8ea58a9c56804e4ff8cff4d',
            'ext': 'mp4',
            'title': 'First day in LBRY? Start HERE!',
            'description': 'md5:f6cb5c704b332d37f5119313c2c98f51',
            'timestamp': 1595694354,
            'upload_date': '20200725',
        }
    }, {
        # Audio
        'url': 'https://lbry.tv/@LBRYFoundation:0/Episode-1:e',
        'md5': 'c94017d3eba9b49ce085a8fad6b98d00',
        'info_dict': {
            'id': 'e7d93d772bd87e2b62d5ab993c1c3ced86ebb396',
            'ext': 'mp3',
            'title': 'The LBRY Foundation Community Podcast Episode 1 - Introduction, Streaming on LBRY, Transcoding',
            'description': 'md5:661ac4f1db09f31728931d7b88807a61',
            'timestamp': 1591312601,
            'upload_date': '20200604',
        }
    }, {
        'url': 'https://odysee.com/@BrodieRobertson:5/apple-is-tracking-everything-you-do-on:e',
        'only_matching': True,
    }]

    def _call_api_proxy(self, method, display_id, params):
        return self._download_json(
            'https://api.lbry.tv/api/v1/proxy', display_id,
            headers={'Content-Type': 'application/json-rpc'},
            data=json.dumps({
                'method': method,
                'params': params,
            }).encode())['result']

    def _real_extract(self, url):
        display_id = self._match_id(url).replace(':', '#')
        uri = 'lbry://' + display_id
        result = self._call_api_proxy(
            'resolve', display_id, {'urls': [uri]})[uri]
        result_value = result['value']
        if result_value.get('stream_type') not in ('video', 'audio'):
            raise ExtractorError('Unsupported URL', expected=True)
        streaming_url = self._call_api_proxy(
            'get', display_id, {'uri': uri})['streaming_url']
        source = result_value.get('source') or {}
        media = result_value.get('video') or result_value.get('audio') or {}
        signing_channel = result_value.get('signing_channel') or {}

        return {
            'id': result['claim_id'],
            'title': result_value['title'],
            'thumbnail': try_get(result_value, lambda x: x['thumbnail']['url'], compat_str),
            'description': result_value.get('description'),
            'license': result_value.get('license'),
            'timestamp': int_or_none(result.get('timestamp')),
            'tags': result_value.get('tags'),
            'width': int_or_none(media.get('width')),
            'height': int_or_none(media.get('height')),
            'duration': int_or_none(media.get('duration')),
            'channel': signing_channel.get('name'),
            'channel_id': signing_channel.get('claim_id'),
            'ext': determine_ext(source.get('name')) or mimetype2ext(source.get('media_type')),
            'filesize': int_or_none(source.get('size')),
            'url': streaming_url,
        }
