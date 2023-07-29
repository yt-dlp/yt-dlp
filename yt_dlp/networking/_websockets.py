# Request handler for https://github.com/python-websockets/websockets

from __future__ import annotations

import asyncio
import atexit
import io
import logging
import urllib.parse
import sys

from .common import register_rh
from .exceptions import TransportError
from .websocket import WebSocketResponse, WebSocketRequestHandler
from ..dependencies import websockets

if not websockets:
    raise ImportError('websockets is not installed')

import websockets.sync.client


class WebsocketsResponseAdapter(WebSocketResponse):

    def __init__(self, wsw: websockets.sync.client.ClientConnection, url):
        super().__init__(io.BytesIO(b''), url=url, headers=wsw.response.headers, status=101)
        self.wsw = wsw

    def close(self, status=None):
        self.wsw.__exit__(None, None, None)
        super().close()

    def send(self, *args):
        return self.wsw.send(*args)

    def recv(self, *args):
        return self.wsw.recv(*args)


@register_rh
class WebsocketsRH(WebSocketRequestHandler):
    _SUPPORTED_URL_SCHEMES = ('wss', 'ws')
    RH_NAME = 'websockets'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('websockets.client', 'websockets.server'):
            logger = logging.getLogger(name)
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setFormatter(logging.Formatter(f'{self.RH_NAME}: %(message)s'))
            logger.addHandler(handler)
            if self.verbose:
                logger.setLevel(logging.DEBUG)

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('timeout', None)

    def _send(self, request):
        ws_kwargs = {}
        if urllib.parse.urlparse(request.url).scheme == 'wss':
            ws_kwargs['ssl_context'] = self._make_sslcontext()

        source_address = self.source_address
        if source_address is not None:
            ws_kwargs['source_address'] = source_address
        timeout = float(request.extensions.get('timeout') or self.timeout)
        try:
            conn = websockets.sync.client.connect(
                request.url, additional_headers=self._merge_headers(request.headers), open_timeout=timeout, **ws_kwargs)
            return WebsocketsResponseAdapter(conn, url=request.url)
        except TimeoutError as e:
            raise TransportError(cause=e) from e

