from __future__ import annotations

import contextlib
import io
import logging
import ssl
import sys

from ._helper import (
    create_connection,
    create_socks_proxy_socket,
    make_socks_proxy_opts,
    select_proxy,
)
from .common import Features, Response, register_rh
from .exceptions import (
    CertificateVerifyError,
    HTTPError,
    ProxyError,
    RequestError,
    SSLError,
    TransportError,
)
from .websocket import WebSocketRequestHandler, WebSocketResponse
from ..compat import functools
from ..dependencies import websockets
from ..socks import ProxyError as SocksProxyError
from ..utils import int_or_none

if not websockets:
    raise ImportError('websockets is not installed')

import websockets.version

websockets_version = tuple(map(int_or_none, websockets.version.version.split('.')))
if websockets_version < (12, 0):
    raise ImportError('Only websockets>=12.0 is supported')

import websockets.sync.client
from websockets.uri import parse_uri

# In websockets Connection, recv_exc and recv_events_exc are defined
# after the recv events handler thread is started [1].
# On our CI using PyPy, in some cases a race condition may occur
# where the recv events handler thread tries to use these attributes before they are defined [2].
# 1: https://github.com/python-websockets/websockets/blame/de768cf65e7e2b1a3b67854fb9e08816a5ff7050/src/websockets/sync/connection.py#L93
# 2: "AttributeError: 'ClientConnection' object has no attribute 'recv_events_exc'. Did you mean: 'recv_events'?"
import websockets.sync.connection  # isort: split
with contextlib.suppress(Exception):
    # > 12.0
    websockets.sync.connection.Connection.recv_exc = None
    # 12.0
    websockets.sync.connection.Connection.recv_events_exc = None


class WebsocketsResponseAdapter(WebSocketResponse):

    def __init__(self, ws: websockets.sync.client.ClientConnection, url):
        super().__init__(
            fp=io.BytesIO(ws.response.body or b''),
            url=url,
            headers=ws.response.headers,
            status=ws.response.status_code,
            reason=ws.response.reason_phrase,
        )
        self._ws = ws

    def close(self):
        self._ws.close()
        super().close()

    def send(self, message):
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.send
        try:
            return self._ws.send(message)
        except (websockets.exceptions.WebSocketException, RuntimeError, TimeoutError) as e:
            raise TransportError(cause=e) from e
        except SocksProxyError as e:
            raise ProxyError(cause=e) from e
        except TypeError as e:
            raise RequestError(cause=e) from e

    def recv(self):
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.recv
        try:
            return self._ws.recv()
        except SocksProxyError as e:
            raise ProxyError(cause=e) from e
        except (websockets.exceptions.WebSocketException, RuntimeError, TimeoutError) as e:
            raise TransportError(cause=e) from e


@register_rh
class WebsocketsRH(WebSocketRequestHandler):
    """
    Websockets request handler
    https://websockets.readthedocs.io
    https://github.com/python-websockets/websockets
    """
    _SUPPORTED_URL_SCHEMES = ('wss', 'ws')
    _SUPPORTED_PROXY_SCHEMES = ('socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_FEATURES = (Features.ALL_PROXY, Features.NO_PROXY)
    RH_NAME = 'websockets'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logging_handlers = {}
        for name in ('websockets.client', 'websockets.server'):
            logger = logging.getLogger(name)
            handler = logging.StreamHandler(stream=sys.stdout)
            handler.setFormatter(logging.Formatter(f'{self.RH_NAME}: %(message)s'))
            self.__logging_handlers[name] = handler
            logger.addHandler(handler)
            if self.verbose:
                logger.setLevel(logging.DEBUG)

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('timeout', None)
        extensions.pop('cookiejar', None)

    def close(self):
        # Remove the logging handler that contains a reference to our logger
        # See: https://github.com/yt-dlp/yt-dlp/issues/8922
        for name, handler in self.__logging_handlers.items():
            logging.getLogger(name).removeHandler(handler)

    def _send(self, request):
        timeout = self._calculate_timeout(request)
        headers = self._merge_headers(request.headers)
        if 'cookie' not in headers:
            cookiejar = self._get_cookiejar(request)
            cookie_header = cookiejar.get_cookie_header(request.url)
            if cookie_header:
                headers['cookie'] = cookie_header

        wsuri = parse_uri(request.url)
        create_conn_kwargs = {
            'source_address': (self.source_address, 0) if self.source_address else None,
            'timeout': timeout,
        }
        proxy = select_proxy(request.url, self._get_proxies(request))
        try:
            if proxy:
                socks_proxy_options = make_socks_proxy_opts(proxy)
                sock = create_connection(
                    address=(socks_proxy_options['addr'], socks_proxy_options['port']),
                    _create_socket_func=functools.partial(
                        create_socks_proxy_socket, (wsuri.host, wsuri.port), socks_proxy_options),
                    **create_conn_kwargs,
                )
            else:
                sock = create_connection(
                    address=(wsuri.host, wsuri.port),
                    **create_conn_kwargs,
                )
            conn = websockets.sync.client.connect(
                sock=sock,
                uri=request.url,
                additional_headers=headers,
                open_timeout=timeout,
                user_agent_header=None,
                ssl_context=self._make_sslcontext() if wsuri.secure else None,
                close_timeout=0,  # not ideal, but prevents yt-dlp hanging
            )
            return WebsocketsResponseAdapter(conn, url=request.url)

        # Exceptions as per https://websockets.readthedocs.io/en/stable/reference/sync/client.html
        except SocksProxyError as e:
            raise ProxyError(cause=e) from e
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
        except (OSError, TimeoutError, websockets.exceptions.WebSocketException) as e:
            raise TransportError(cause=e) from e
