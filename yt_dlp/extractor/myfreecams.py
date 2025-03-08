import json
import random
import re
import urllib.parse

from .common import InfoExtractor
from ..dependencies import websockets
from ..utils import ExtractorError


class MyFreeCamsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myfreecams\.com/#(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.myfreecams.com/#Elise_wood',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': 'Elise_wood',
            'ext': 'mp4',
            'title': r're:Elise_wood',
            'description': r're:MyFreeCams',
            'age_limit': 18,
            'is_live': True,
            'live_status': str,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Model is currently offline',
    }]

    JS_SERVER_URL = 'https://www.myfreecams.com/_js/serverconfig.js'

    _dict_re = re.compile(r'''(?P<data>{.*})''')
    _socket_re = re.compile(r'''(\w+) (\w+) (\w+) (\w+) (\w+)''')

    def _get_servers(self):
        return self._download_json(
            self.JS_SERVER_URL, self.video_id,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            }, fatal=False, impersonate=False) or {}

    def _websocket_data(self, username, chat_servers):
        try_to_connect = 0
        xchat = None
        host = None
        while try_to_connect < 5:
            try:
                xchat = str(random.choice(chat_servers))
                host = f'wss://{xchat}.myfreecams.com/fcsl'
                ws = websockets.sync.client.connect(host)
                ws.send('fcsws_20180422\n\0')
                ws.send('1 0 0 20071025 0 1/guest:guest\n\0')
                self.write_debug(f'Websocket server {xchat} connected')
                self.write_debug(f'Websocket URL: {host}')
                try_to_connect = 5
            except websockets.exceptions.WebSocketException:
                try_to_connect += 1
                self.report_warning(f'Failed to connect to WS server: {xchat} - try {try_to_connect}')
                if try_to_connect == 5:
                    error = f'Failed to connect to WS server: {host}'
                    raise ExtractorError(error)

        buff = ''
        php_message = ''
        ws_close = 0
        while ws_close == 0:
            socket_buffer = ws.recv()
            socket_buffer = buff + socket_buffer
            buff = ''
            while True:
                ws_answer = self._socket_re.search(socket_buffer)
                if bool(ws_answer) == 0:
                    break

                FC = ws_answer.group(1)
                FCTYPE = int(FC[6:])

                message_length = int(FC[0:6])
                message = socket_buffer[6:6 + message_length]

                if len(message) < message_length:
                    buff = ''.join(socket_buffer)
                    break

                message = urllib.parse.unquote(message)

                if FCTYPE == 1 and username:
                    ws.send(f'10 0 0 20 0 {username}\n')
                elif FCTYPE == 81:
                    php_message = message
                    if username is None:
                        ws_close = 1
                elif FCTYPE == 10:
                    ws_close = 1

                socket_buffer = socket_buffer[6 + message_length:]

                if len(socket_buffer) == 0:
                    break

        ws.send('99 0 0 0 0')
        ws.close()
        return message, php_message

    def _get_camserver(self, servers, key):
        server_type = None
        value = None

        h5video_servers = servers['h5video_servers']
        ngvideo_servers = servers['ngvideo_servers']
        wzobs_servers = servers['wzobs_servers']

        if h5video_servers.get(str(key)):
            value = h5video_servers[str(key)]
            server_type = 'h5video_servers'
        elif wzobs_servers.get(str(key)):
            value = wzobs_servers[str(key)]
            server_type = 'wzobs_servers'
        elif ngvideo_servers.get(str(key)):
            value = ngvideo_servers[str(key)]
            server_type = 'ngvideo_servers'

        return value, server_type

    def _get_streams(self, url):
        self.video_id = self._match_id(url)
        webpage = self._download_webpage(url, self.video_id)

        servers = self._get_servers()
        chat_servers = servers['chat_servers']

        message, php_message = self._websocket_data(self.video_id, chat_servers)

        if self.video_id:
            self.write_debug('Attempting to use WebSocket data')
            data = self._dict_re.search(message)
            if data is None:
                raise ExtractorError('Could not find data in WebSocket message')
            data = parse_json(data.group('data'))

        vs = data['vs']
        ok_vs = [0, 90]
        if vs not in ok_vs:
            if vs == 2:
                error = ('Model is currently away')
            elif vs == 12:
                error = ('Model is currently in a private show')
            elif vs == 13:
                error = ('Model is currently in a group show')
            elif vs == 14:
                error = ('Model is currently in a club show')
            elif vs == 127:
                error = ('Model is currently offline')
            else:
                error = (f'Stream status: {vs}')
            raise ExtractorError(error, expected=True)

        self.write_debug(f'VS: {vs}')

        nm = data['nm']
        uid = data['uid']
        uid_video = uid + 100000000
        camserver = data['u']['camserv']

        server, server_type = self._get_camserver(servers, camserver)

        self.write_debug(f'Username: {nm}')
        self.write_debug(f'User ID:  {uid}')

        if not server:
            raise ExtractorError('Missing video server')

        self.write_debug(f'Video server: {server}')
        self.write_debug(f'Video server_type: {server_type}')

        if server_type == 'h5video_servers':
            # DASH_VIDEO_URL = f'https://{server}.myfreecams.com/NxServer/ngrp:mfc_{uid_video}.f4v_desktop/manifest.mpd'
            HLS_VIDEO_URL = f'https://{server}.myfreecams.com/NxServer/ngrp:mfc_{uid_video}.f4v_mobile/playlist.m3u8'
        elif server_type == 'wzobs_servers':
            # DASH_VIDEO_URL = ''
            HLS_VIDEO_URL = f'https://{server}.myfreecams.com/NxServer/ngrp:mfc_a_{uid_video}.f4v_mobile/playlist.m3u8'
        elif server_type == 'ngvideo_servers':
            raise ExtractorError('ngvideo_servers are not supported.')
        else:
            raise ExtractorError('Unknow server type.')

        self.write_debug(f'HLS URL: {HLS_VIDEO_URL}')

        return {
            'id': self.video_id,
            'title': self._html_extract_title(html=webpage, default=self.video_id),
            'description': self._html_search_meta('description', webpage, default=None),
            'formats': self._extract_m3u8_formats(HLS_VIDEO_URL, self.video_id, ext='mp4', live=True),
            'age_limit': self._rta_search(webpage),
            'is_live': True,
        }

    def _real_extract(self, url):
        self.write_debug(self._get_streams(url=url))
        return self._get_streams(url=url)


def _parse(parser, data, name, *args, **kwargs):
    try:
        parsed = parser(data, *args, **kwargs)
    except Exception as err:
        snippet = repr(data)
        if len(snippet) > 35:
            snippet = f'{snippet[:35]} ...'

        raise ExtractorError(f'Unable to parse {name}: {err} ({snippet})')

    return parsed


def parse_json(
    data,
    name='JSON',
    schema=None,
    *args,
    **kwargs,
):
    """Wrapper around json.loads.

    Provides these extra features:
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    return _parse(*args, **kwargs, parser=json.loads, data=data, name=name)
