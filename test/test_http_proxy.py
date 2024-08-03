import abc
import base64
import contextlib
import functools
import json
import os
import random
import ssl
import threading
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingTCPServer

import pytest

from test.helper import http_server_port, verify_address_availability
from test.test_networking import TEST_DIR
from test.test_socks import IPv6ThreadingTCPServer
from yt_dlp.dependencies import urllib3
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import HTTPError, ProxyError, SSLError


class HTTPProxyAuthMixin:

    def proxy_auth_error(self):
        self.send_response(407)
        self.send_header('Proxy-Authenticate', 'Basic realm="test http proxy"')
        self.end_headers()
        return False

    def do_proxy_auth(self, username, password):
        if username is None and password is None:
            return True

        proxy_auth_header = self.headers.get('Proxy-Authorization', None)
        if proxy_auth_header is None:
            return self.proxy_auth_error()

        if not proxy_auth_header.startswith('Basic '):
            return self.proxy_auth_error()

        auth = proxy_auth_header[6:]

        try:
            auth_username, auth_password = base64.b64decode(auth).decode().split(':', 1)
        except Exception:
            return self.proxy_auth_error()

        if auth_username != (username or '') or auth_password != (password or ''):
            return self.proxy_auth_error()
        return True


class HTTPProxyHandler(BaseHTTPRequestHandler, HTTPProxyAuthMixin):
    def __init__(self, *args, proxy_info=None, username=None, password=None, request_handler=None, **kwargs):
        self.username = username
        self.password = password
        self.proxy_info = proxy_info
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if not self.do_proxy_auth(self.username, self.password):
            self.server.close_request(self.request)
            return
        if self.path.endswith('/proxy_info'):
            payload = json.dumps(self.proxy_info or {
                'client_address': self.client_address,
                'connect': False,
                'connect_host': None,
                'connect_port': None,
                'headers': dict(self.headers),
                'path': self.path,
                'proxy': ':'.join(str(y) for y in self.connection.getsockname()),
            })
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload.encode())
        else:
            self.send_response(404)
            self.end_headers()

        self.server.close_request(self.request)


if urllib3:
    import urllib3.util.ssltransport

    class SSLTransport(urllib3.util.ssltransport.SSLTransport):
        """
        Modified version of urllib3 SSLTransport to support server side SSL

        This allows us to chain multiple TLS connections.
        """

        def __init__(self, socket, ssl_context, server_hostname=None, suppress_ragged_eofs=True, server_side=False):
            self.incoming = ssl.MemoryBIO()
            self.outgoing = ssl.MemoryBIO()

            self.suppress_ragged_eofs = suppress_ragged_eofs
            self.socket = socket

            self.sslobj = ssl_context.wrap_bio(
                self.incoming,
                self.outgoing,
                server_hostname=server_hostname,
                server_side=server_side,
            )
            self._ssl_io_loop(self.sslobj.do_handshake)

        @property
        def _io_refs(self):
            return self.socket._io_refs

        @_io_refs.setter
        def _io_refs(self, value):
            self.socket._io_refs = value

        def shutdown(self, *args, **kwargs):
            self.socket.shutdown(*args, **kwargs)
else:
    SSLTransport = None


class HTTPSProxyHandler(HTTPProxyHandler):
    def __init__(self, request, *args, **kwargs):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.load_cert_chain(certfn, None)
        if isinstance(request, ssl.SSLSocket):
            request = SSLTransport(request, ssl_context=sslctx, server_side=True)
        else:
            request = sslctx.wrap_socket(request, server_side=True)
        super().__init__(request, *args, **kwargs)


class HTTPConnectProxyHandler(BaseHTTPRequestHandler, HTTPProxyAuthMixin):
    protocol_version = 'HTTP/1.1'
    default_request_version = 'HTTP/1.1'

    def __init__(self, *args, username=None, password=None, request_handler=None, **kwargs):
        self.username = username
        self.password = password
        self.request_handler = request_handler
        super().__init__(*args, **kwargs)

    def do_CONNECT(self):
        if not self.do_proxy_auth(self.username, self.password):
            self.server.close_request(self.request)
            return
        self.send_response(200)
        self.end_headers()
        proxy_info = {
            'client_address': self.client_address,
            'connect': True,
            'connect_host': self.path.split(':')[0],
            'connect_port': int(self.path.split(':')[1]),
            'headers': dict(self.headers),
            'path': self.path,
            'proxy': ':'.join(str(y) for y in self.connection.getsockname()),
        }
        self.request_handler(self.request, self.client_address, self.server, proxy_info=proxy_info)
        self.server.close_request(self.request)


class HTTPSConnectProxyHandler(HTTPConnectProxyHandler):
    def __init__(self, request, *args, **kwargs):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.load_cert_chain(certfn, None)
        request = sslctx.wrap_socket(request, server_side=True)
        self._original_request = request
        super().__init__(request, *args, **kwargs)

    def do_CONNECT(self):
        super().do_CONNECT()
        self.server.close_request(self._original_request)


@contextlib.contextmanager
def proxy_server(proxy_server_class, request_handler, bind_ip=None, **proxy_server_kwargs):
    server = server_thread = None
    try:
        bind_address = bind_ip or '127.0.0.1'
        server_type = ThreadingTCPServer if '.' in bind_address else IPv6ThreadingTCPServer
        server = server_type(
            (bind_address, 0), functools.partial(proxy_server_class, request_handler=request_handler, **proxy_server_kwargs))
        server_port = http_server_port(server)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        if '.' not in bind_address:
            yield f'[{bind_address}]:{server_port}'
        else:
            yield f'{bind_address}:{server_port}'
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(2.0)


class HTTPProxyTestContext(abc.ABC):
    REQUEST_HANDLER_CLASS = None
    REQUEST_PROTO = None

    def http_server(self, server_class, *args, **kwargs):
        return proxy_server(server_class, self.REQUEST_HANDLER_CLASS, *args, **kwargs)

    @abc.abstractmethod
    def proxy_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs) -> dict:
        """return a dict of proxy_info"""


class HTTPProxyHTTPTestContext(HTTPProxyTestContext):
    # Standard HTTP Proxy for http requests
    REQUEST_HANDLER_CLASS = HTTPProxyHandler
    REQUEST_PROTO = 'http'

    def proxy_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs):
        request = Request(f'http://{target_domain or "127.0.0.1"}:{target_port or "40000"}/proxy_info', **req_kwargs)
        handler.validate(request)
        return json.loads(handler.send(request).read().decode())


class HTTPProxyHTTPSTestContext(HTTPProxyTestContext):
    # HTTP Connect proxy, for https requests
    REQUEST_HANDLER_CLASS = HTTPSProxyHandler
    REQUEST_PROTO = 'https'

    def proxy_info_request(self, handler, target_domain=None, target_port=None, **req_kwargs):
        request = Request(f'https://{target_domain or "127.0.0.1"}:{target_port or "40000"}/proxy_info', **req_kwargs)
        handler.validate(request)
        return json.loads(handler.send(request).read().decode())


CTX_MAP = {
    'http': HTTPProxyHTTPTestContext,
    'https': HTTPProxyHTTPSTestContext,
}


@pytest.fixture(scope='module')
def ctx(request):
    return CTX_MAP[request.param]()


@pytest.mark.parametrize(
    'handler', ['Urllib', 'Requests', 'CurlCFFI'], indirect=True)
@pytest.mark.parametrize('ctx', ['http'], indirect=True)  # pure http proxy can only support http
class TestHTTPProxy:
    def test_http_no_auth(self, handler, ctx):
        with ctx.http_server(HTTPProxyHandler) as server_address:
            with handler(proxies={ctx.REQUEST_PROTO: f'http://{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert proxy_info['connect'] is False
                assert 'Proxy-Authorization' not in proxy_info['headers']

    def test_http_auth(self, handler, ctx):
        with ctx.http_server(HTTPProxyHandler, username='test', password='test') as server_address:
            with handler(proxies={ctx.REQUEST_PROTO: f'http://test:test@{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert 'Proxy-Authorization' in proxy_info['headers']

    def test_http_bad_auth(self, handler, ctx):
        with ctx.http_server(HTTPProxyHandler, username='test', password='test') as server_address:
            with handler(proxies={ctx.REQUEST_PROTO: f'http://test:bad@{server_address}'}) as rh:
                with pytest.raises(HTTPError) as exc_info:
                    ctx.proxy_info_request(rh)
                assert exc_info.value.response.status == 407
                exc_info.value.response.close()

    def test_http_source_address(self, handler, ctx):
        with ctx.http_server(HTTPProxyHandler) as server_address:
            source_address = f'127.0.0.{random.randint(5, 255)}'
            verify_address_availability(source_address)
            with handler(proxies={ctx.REQUEST_PROTO: f'http://{server_address}'},
                         source_address=source_address) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert proxy_info['client_address'][0] == source_address

    @pytest.mark.skip_handler('Urllib', 'urllib does not support https proxies')
    def test_https(self, handler, ctx):
        with ctx.http_server(HTTPSProxyHandler) as server_address:
            with handler(verify=False, proxies={ctx.REQUEST_PROTO: f'https://{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert proxy_info['connect'] is False
                assert 'Proxy-Authorization' not in proxy_info['headers']

    @pytest.mark.skip_handler('Urllib', 'urllib does not support https proxies')
    def test_https_verify_failed(self, handler, ctx):
        with ctx.http_server(HTTPSProxyHandler) as server_address:
            with handler(verify=True, proxies={ctx.REQUEST_PROTO: f'https://{server_address}'}) as rh:
                # Accept SSLError as may not be feasible to tell if it is proxy or request error.
                # note: if request proto also does ssl verification, this may also be the error of the request.
                # Until we can support passing custom cacerts to handlers, we cannot properly test this for all cases.
                with pytest.raises((ProxyError, SSLError)):
                    ctx.proxy_info_request(rh)

    def test_http_with_idn(self, handler, ctx):
        with ctx.http_server(HTTPProxyHandler) as server_address:
            with handler(proxies={ctx.REQUEST_PROTO: f'http://{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh, target_domain='中文.tw')
                assert proxy_info['proxy'] == server_address
                assert proxy_info['path'].startswith('http://xn--fiq228c.tw')
                assert proxy_info['headers']['Host'].split(':', 1)[0] == 'xn--fiq228c.tw'


@pytest.mark.parametrize(
    'handler,ctx', [
        ('Requests', 'https'),
        ('CurlCFFI', 'https'),
    ], indirect=True)
class TestHTTPConnectProxy:
    def test_http_connect_no_auth(self, handler, ctx):
        with ctx.http_server(HTTPConnectProxyHandler) as server_address:
            with handler(verify=False, proxies={ctx.REQUEST_PROTO: f'http://{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert proxy_info['connect'] is True
                assert 'Proxy-Authorization' not in proxy_info['headers']

    def test_http_connect_auth(self, handler, ctx):
        with ctx.http_server(HTTPConnectProxyHandler, username='test', password='test') as server_address:
            with handler(verify=False, proxies={ctx.REQUEST_PROTO: f'http://test:test@{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert 'Proxy-Authorization' in proxy_info['headers']

    @pytest.mark.skip_handler(
        'Requests',
        'bug in urllib3 causes unclosed socket: https://github.com/urllib3/urllib3/issues/3374',
    )
    def test_http_connect_bad_auth(self, handler, ctx):
        with ctx.http_server(HTTPConnectProxyHandler, username='test', password='test') as server_address:
            with handler(verify=False, proxies={ctx.REQUEST_PROTO: f'http://test:bad@{server_address}'}) as rh:
                with pytest.raises(ProxyError):
                    ctx.proxy_info_request(rh)

    def test_http_connect_source_address(self, handler, ctx):
        with ctx.http_server(HTTPConnectProxyHandler) as server_address:
            source_address = f'127.0.0.{random.randint(5, 255)}'
            verify_address_availability(source_address)
            with handler(proxies={ctx.REQUEST_PROTO: f'http://{server_address}'},
                         source_address=source_address,
                         verify=False) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert proxy_info['client_address'][0] == source_address

    @pytest.mark.skipif(urllib3 is None, reason='requires urllib3 to test')
    def test_https_connect_proxy(self, handler, ctx):
        with ctx.http_server(HTTPSConnectProxyHandler) as server_address:
            with handler(verify=False, proxies={ctx.REQUEST_PROTO: f'https://{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert proxy_info['connect'] is True
                assert 'Proxy-Authorization' not in proxy_info['headers']

    @pytest.mark.skipif(urllib3 is None, reason='requires urllib3 to test')
    def test_https_connect_verify_failed(self, handler, ctx):
        with ctx.http_server(HTTPSConnectProxyHandler) as server_address:
            with handler(verify=True, proxies={ctx.REQUEST_PROTO: f'https://{server_address}'}) as rh:
                # Accept SSLError as may not be feasible to tell if it is proxy or request error.
                # note: if request proto also does ssl verification, this may also be the error of the request.
                # Until we can support passing custom cacerts to handlers, we cannot properly test this for all cases.
                with pytest.raises((ProxyError, SSLError)):
                    ctx.proxy_info_request(rh)

    @pytest.mark.skipif(urllib3 is None, reason='requires urllib3 to test')
    def test_https_connect_proxy_auth(self, handler, ctx):
        with ctx.http_server(HTTPSConnectProxyHandler, username='test', password='test') as server_address:
            with handler(verify=False, proxies={ctx.REQUEST_PROTO: f'https://test:test@{server_address}'}) as rh:
                proxy_info = ctx.proxy_info_request(rh)
                assert proxy_info['proxy'] == server_address
                assert 'Proxy-Authorization' in proxy_info['headers']
