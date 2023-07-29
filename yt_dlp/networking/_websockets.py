# Request handler for https://github.com/python-websockets/websockets

from __future__ import annotations

import asyncio
import atexit
import io
import logging
import urllib.parse
import sys

from .common import register_rh
from .exceptions import TransportError, RequestError
from .websocket import WebSocketResponse, WebSocketRequestHandler
from ..dependencies import websockets

if not websockets:
    raise ImportError('websockets is not installed')

import websockets.sync.client
from websockets.exceptions import InvalidHandshake, InvalidURI, ConnectionClosed


class WebsocketsResponseAdapter(WebSocketResponse):

    def __init__(self, wsw: websockets.sync.client.ClientConnection, url):
        super().__init__(
            fp=io.BytesIO(wsw.response.body or b''),  # TODO: test
            url=url,
            headers=wsw.response.headers,  # TODO: test multiple headers (may need to use raw_items())
            status=wsw.response.status_code,
            reason=wsw.response.reason_phrase,
        )
        self.wsw = wsw

    def close(self, status=None):
        self.wsw.close()
        super().close()

    def send(self, *args):
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.send
        try:
            return self.wsw.send(*args)
        except (ConnectionClosed, RuntimeError) as e:
            raise TransportError(cause=e) from e
        except TypeError as e:
            raise RequestError(cause=e) from e

    def recv(self, *args):
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.recv
        try:
            return self.wsw.recv(*args)
        except (ConnectionClosed, RuntimeError) as e:
            raise TransportError(cause=e) from e


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
        """
        https://websockets.readthedocs.io/en/stable/reference/sync/client.html
        TODO:
        - Cookie Support
        - Test Exception Mapping
        - Timeout handling for closing?
        - WS Pinging
        - KeyboardInterrupt doesn't seem to kill websockets
        """
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

        # Exceptions as per https://websockets.readthedocs.io/en/stable/reference/sync/client.html
        except InvalidURI as e:
            raise RequestError(cause=e) from e
        except (OSError, TimeoutError, InvalidHandshake) as e:
            raise TransportError(cause=e) from e

