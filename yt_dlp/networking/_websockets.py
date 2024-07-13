from __future__ import annotations

import contextlib
import io
import logging
import ssl
import urllib.parse

from ._helper import (
    create_connection,
    create_http_connect_connection,
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
    UnsupportedRequest,
)
from .websocket import WebSocketRequestHandler, WebSocketResponse
from ..compat import functools
from ..dependencies import urllib3, websockets
from ..socks import ProxyError as SocksProxyError
from ..utils import int_or_none

if not websockets:
    raise ImportError('websockets is not installed')

import websockets.version

websockets_version = tuple(map(int_or_none, websockets.version.version.split('.')))
if websockets_version < (12, 0):
    raise ImportError('Only websockets>=12.0 is supported')

urllib3_supported = False
urllib3_version = tuple(int_or_none(x, default=0) for x in urllib3.__version__.split('.')) if urllib3 else None
if urllib3_version and urllib3_version >= (1, 26, 17):
    urllib3_supported = True


# Disable apply_mask C implementation
# Seems to help reduce "Fatal Python error: Aborted" in CI
with contextlib.suppress(Exception):
    import websockets.frames
    import websockets.legacy.framing
    import websockets.utils
    websockets.frames.apply_mask = websockets.legacy.framing = websockets.utils.apply_mask

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


class WebsocketsLoggingHandler(logging.Handler):
    """Redirect websocket logs to our logger"""

    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            self.handleError(record)
        else:
            self._logger.stdout(msg)


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
    _SUPPORTED_PROXY_SCHEMES = ('socks4', 'socks4a', 'socks5', 'socks5h', 'http', 'https')
    _SUPPORTED_FEATURES = (Features.ALL_PROXY, Features.NO_PROXY)
    RH_NAME = 'websockets'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logging_handlers = {}
        for name in ('websockets.client', 'websockets.server'):
            logger = logging.getLogger(name)
            handler = WebsocketsLoggingHandler(logger=self._logger)
            handler.setFormatter(logging.Formatter(f'{self.RH_NAME}: [{name}] %(message)s'))
            self.__logging_handlers[name] = handler
            logger.addHandler(handler)
            if self.verbose:
                logger.setLevel(logging.DEBUG)

    def _validate(self, request):
        super()._validate(request)
        proxy = select_proxy(request.url, self._get_proxies(request))
        if (
            proxy
            and urllib.parse.urlparse(proxy).scheme.lower() == 'https'
            and urllib.parse.urlparse(request.url).scheme.lower() == 'wss'
            and not urllib3_supported
        ):
            raise UnsupportedRequest('WSS over HTTPS proxy requires a supported version of urllib3')

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('timeout', None)
        extensions.pop('cookiejar', None)

    def close(self):
        # Remove the logging handler that contains a reference to our logger
        # See: https://github.com/yt-dlp/yt-dlp/issues/8922
        for name, handler in self.__logging_handlers.items():
            logging.getLogger(name).removeHandler(handler)

    def _make_sock(self, proxy, url, timeout):
        create_conn_kwargs = {
            'source_address': (self.source_address, 0) if self.source_address else None,
            'timeout': timeout
        }
        parsed_url = parse_uri(url)
        parsed_proxy_url = urllib.parse.urlparse(proxy)
        if proxy:
            if parsed_proxy_url.scheme.startswith('socks'):
                socks_proxy_options = make_socks_proxy_opts(proxy)
                return create_connection(
                    address=(socks_proxy_options['addr'], socks_proxy_options['port']),
                    _create_socket_func=functools.partial(
                        create_socks_proxy_socket, (parsed_url.host, parsed_url.port), socks_proxy_options),
                    **create_conn_kwargs,
                )

            elif parsed_proxy_url.scheme in ('http', 'https'):
                return create_http_connect_connection(
                    proxy_port=parsed_proxy_url.port,
                    proxy_host=parsed_proxy_url.hostname,
                    connect_port=parsed_url.port,
                    connect_host=parsed_url.host,
                    timeout=timeout,
                    ssl_context=self._make_sslcontext() if parsed_proxy_url.scheme == 'https' else None,
                    source_address=self.source_address,
                    username=parsed_proxy_url.username,
                    password=parsed_proxy_url.password,
                    debug=self.verbose,
                )
        return create_connection(
            address=(parsed_url.host, parsed_url.port),
            **create_conn_kwargs,
        )

    def _send(self, request):
        timeout = self._calculate_timeout(request)
        headers = self._merge_headers(request.headers)
        if 'cookie' not in headers:
            cookiejar = self._get_cookiejar(request)
            cookie_header = cookiejar.get_cookie_header(request.url)
            if cookie_header:
                headers['cookie'] = cookie_header

        proxy = select_proxy(request.url, self._get_proxies(request))

        try:
            ssl_context = None
            sock = self._make_sock(proxy, request.url, timeout)
            if parse_uri(request.url).secure:
                ssl_context = WebsocketsSSLContext(self._make_sslcontext())
            conn = websockets.sync.client.connect(
                sock=sock,
                uri=request.url,
                additional_headers=headers,
                open_timeout=timeout,
                user_agent_header=None,
                ssl_context=ssl_context,
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


if urllib3_supported:
    from urllib3.util.ssltransport import SSLTransport

    class WebsocketsSSLTransport(SSLTransport):
        """
        Modified version of urllib3 SSLTransport to support additional operations used by websockets
        """
        def setsockopt(self, *args, **kwargs):
            self.socket.setsockopt(*args, **kwargs)

        def shutdown(self, *args, **kwargs):
            self.unwrap()
            self.socket.shutdown(*args, **kwargs)

        def _wrap_ssl_read(self, *args, **kwargs):
            res = super()._wrap_ssl_read(*args, **kwargs)
            if res == 0:
                # Websockets does not treat 0 as an EOF, rather only b''
                return b''
            return res
else:
    WebsocketsSSLTransport = None


class WebsocketsSSLContext:
    """
    Dummy SSL Context for websockets which returns a WebsocketsSSLTransport instance
    for wrap socket when using TLS-in-TLS.
    """
    def __init__(self, ssl_context: ssl.SSLContext):
        self.ssl_context = ssl_context

    def wrap_socket(self, sock, server_hostname=None):
        if isinstance(sock, ssl.SSLSocket) and WebsocketsSSLTransport:
            return WebsocketsSSLTransport(sock, self.ssl_context, server_hostname=server_hostname)
        return self.ssl_context.wrap_socket(sock, server_hostname=server_hostname)
