from .common import InfoExtractor
from ..utils import ExtractorError, try_get


class SaitosanIE(InfoExtractor):
    IE_NAME = 'Saitosan'
    _VALID_URL = r'https?://(?:www\.)?saitosan\.net/bview.html\?id=(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.saitosan.net/bview.html?id=10031846',
        'info_dict': {
            'id': '10031846',
            'ext': 'mp4',
            'title': '井下原 和弥',
            'uploader': '井下原 和弥',
            'thumbnail': 'http://111.171.196.85:8088/921f916f-7f55-4c97-b92e-5d9d0fef8f5f/thumb',
            'is_live': True,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Broadcasts are ephemeral',
    },
        {
        'url': 'http://www.saitosan.net/bview.html?id=10031795',
        'info_dict': {
            'id': '10031795',
            'ext': 'mp4',
            'title': '橋本',
            'uploader': '橋本',
            'thumbnail': 'http://111.171.196.85:8088/1a3933e1-a01a-483b-8931-af15f37f8082/thumb',
            'is_live': True,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Broadcasts are ephemeral',
    }]

    def _real_extract(self, url):
        b_id = self._match_id(url)

        base = 'http://hankachi.saitosan-api.net:8002/socket.io/?transport=polling&EIO=3'
        sid = self._download_socket_json(base, b_id, note='Opening socket').get('sid')
        base += '&sid=' + sid

        self._download_webpage(base, b_id, note='Polling socket')
        payload = '420["room_start_join",{"room_id":"%s"}]' % b_id
        payload = '%s:%s' % (len(payload), payload)

        self._download_webpage(base, b_id, data=payload, note='Polling socket with payload')
        response = self._download_socket_json(base, b_id, note='Polling socket')
        if not response.get('ok'):
            err = response.get('error') or {}
            raise ExtractorError(
                '%s said: %s - %s' % (self.IE_NAME, err.get('code', '?'), err.get('msg', 'Unknown')) if err
                else 'The socket reported that the broadcast could not be joined. Maybe it\'s offline or the URL is incorrect',
                expected=True, video_id=b_id)

        self._download_webpage(base, b_id, data='26:421["room_finish_join",{}]', note='Polling socket')
        b_data = self._download_socket_json(base, b_id, note='Getting broadcast metadata from socket')
        m3u8_url = b_data.get('url')

        self._download_webpage(base, b_id, data='1:1', note='Closing socket', fatal=False)

        return {
            'id': b_id,
            'title': b_data.get('name'),
            'formats': self._extract_m3u8_formats(m3u8_url, b_id, 'mp4', live=True),
            'thumbnail': m3u8_url.replace('av.m3u8', 'thumb'),
            'uploader': try_get(b_data, lambda x: x['broadcast_user']['name']),  # same as title
            'is_live': True
        }
