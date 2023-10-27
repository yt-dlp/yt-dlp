# Request handler for https://github.com/python-websockets/websockets

from __future__ import annotations

import asyncio
import atexit
import io
import logging
import urllib.parse
import sys
import ssl

from ._helper import create_connection

from websockets.uri import parse_uri

from .common import register_rh, Response
from .exceptions import TransportError, RequestError, CertificateVerifyError, SSLError, HTTPError
from .websocket import WebSocketResponse, WebSocketRequestHandler
from ..dependencies import websockets

if not websockets:
    raise ImportError('websockets is not installed')

import websockets.sync.client


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
        except (websockets.exceptions.ConnectionClosed, RuntimeError) as e:
            raise TransportError(cause=e) from e
        except TypeError as e:
            raise RequestError(cause=e) from e

    def recv(self, *args):
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.recv
        try:
            return self.wsw.recv(*args)
        except (websockets.exceptions.ConnectionClosed, RuntimeError) as e:
            raise TransportError(cause=e) from e


@register_rh
class WebsocketsRH(WebSocketRequestHandler):
    """
    Websockets request handler
    https://websockets.readthedocs.io
    """
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
        extensions.pop('cookiejar', None)

    def _send(self, request):
        timeout = float(request.extensions.get('timeout') or self.timeout)
        headers = self._merge_headers(request.headers)
        if 'cookie' not in headers:
            cookiejar = request.extensions.get('cookiejar') or self.cookiejar
            cookie_header = cookiejar.get_cookie_header(request.url)
            if cookie_header:
                headers['cookie'] = cookie_header

        wsuri = parse_uri(request.url)
        try:
            sock = create_connection(
                (wsuri.host, wsuri.port),
                source_address=(self.source_address, 0) if self.source_address else None,
                timeout=timeout
            )
            conn = websockets.sync.client.connect(
                sock=sock,
                uri=request.url,
                additional_headers=headers,
                open_timeout=timeout,
                user_agent_header=None,
                ssl_context=self._make_sslcontext() if wsuri.secure else None,
            )
            return WebsocketsResponseAdapter(conn, url=request.url)

        # Exceptions as per https://websockets.readthedocs.io/en/stable/reference/sync/client.html
        except websockets.exceptions.InvalidURI as e:
            raise RequestError(cause=e) from e
        except ssl.SSLCertVerificationError as e:
            raise CertificateVerifyError(cause=e) from e
        except ssl.SSLError as e:
            raise SSLError(cause=e) from e
        except websockets.exceptions.InvalidStatus as e:
            raise HTTPError(
                Response(
                    fp=io.BytesIO(e.response.body),
                    url=request.url,
                    headers=e.response.headers,
                    status=e.response.status_code,
                    reason=e.response.reason_phrase),
                ) from e
        except (OSError, TimeoutError, websockets.exceptions.InvalidHandshake) as e:
            raise TransportError(cause=e) from e

