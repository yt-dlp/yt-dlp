from __future__ import annotations

import io
import logging
import ssl
import sys

from ._helper import create_connection, select_proxy, make_socks_proxy_opts, create_socks_proxy_socket
from .common import Response, register_rh, Features
from .exceptions import (
    CertificateVerifyError,
    HTTPError,
    RequestError,
    SSLError,
    TransportError, ProxyError,
)
from .websocket import WebSocketRequestHandler, WebSocketResponse
from ..compat import functools
from ..dependencies import websockets
from ..utils import int_or_none
from ..socks import ProxyError as SocksProxyError

if not websockets:
    raise ImportError('websockets is not installed')

import websockets.version

websockets_version = tuple(map(int_or_none, websockets.version.version.split('.')))
if websockets_version < (12, 0):
    raise ImportError('Only websockets>=12.0 is supported')

import websockets.sync.client
from websockets.uri import parse_uri


class WebsocketsResponseAdapter(WebSocketResponse):

    def __init__(self, wsw: websockets.sync.client.ClientConnection, url):
        super().__init__(
            fp=io.BytesIO(wsw.response.body or b''),
            url=url,
            headers=wsw.response.headers,
            status=wsw.response.status_code,
            reason=wsw.response.reason_phrase,
        )
        self.wsw = wsw

    def close(self):
        self.wsw.close()
        super().close()

    def send(self, message):
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.send
        try:
            return self.wsw.send(message)
        except (websockets.exceptions.WebSocketException, RuntimeError, TimeoutError) as e:
            raise TransportError(cause=e) from e
        except SocksProxyError as e:
            raise ProxyError(cause=e) from e
        except TypeError as e:
            raise RequestError(cause=e) from e

    def recv(self):
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.recv
        try:
            return self.wsw.recv()
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
        create_conn_kwargs = {
            'source_address': (self.source_address, 0) if self.source_address else None,
            'timeout': timeout
        }
        proxy = select_proxy(request.url, request.proxies or self.proxies or {})
        try:
            if proxy:
                socks_proxy_options = make_socks_proxy_opts(proxy)
                sock = create_connection(
                    address=(socks_proxy_options['addr'], socks_proxy_options['port']),
                    _create_socket_func=functools.partial(
                        create_socks_proxy_socket, (wsuri.host, wsuri.port), socks_proxy_options),
                    **create_conn_kwargs
                )
            else:
                sock = create_connection(
                    address=(wsuri.host, wsuri.port),
                    **create_conn_kwargs
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
