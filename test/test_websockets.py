#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import time

import pytest

from test.helper import verify_address_availability
from yt_dlp.networking.common import Features, DEFAULT_TIMEOUT

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import http.client
import http.cookiejar
import http.server
import json
import random
import ssl
import threading

from yt_dlp import socks, traverse_obj
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.dependencies import websockets
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import (
    CertificateVerifyError,
    HTTPError,
    ProxyError,
    RequestError,
    SSLError,
    TransportError,
)
from yt_dlp.utils.networking import HTTPHeaderDict

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def websocket_handler(websocket):
    for message in websocket:
        if isinstance(message, bytes):
            if message == b'bytes':
                return websocket.send('2')
        elif isinstance(message, str):
            if message == 'headers':
                return websocket.send(json.dumps(dict(websocket.request.headers)))
            elif message == 'path':
                return websocket.send(websocket.request.path)
            elif message == 'source_address':
                return websocket.send(websocket.remote_address[0])
            elif message == 'str':
                return websocket.send('1')
        return websocket.send(message)


def process_request(self, request):
    if request.path.startswith('/gen_'):
        status = http.HTTPStatus(int(request.path[5:]))
        if 300 <= status.value <= 300:
            return websockets.http11.Response(
                status.value, status.phrase, websockets.datastructures.Headers([('Location', '/')]), b'')
        return self.protocol.reject(status.value, status.phrase)
    elif request.path.startswith('/get_cookie'):
        response = self.protocol.accept(request)
        response.headers['Set-Cookie'] = 'test=ytdlp'
        return response
    return self.protocol.accept(request)


def create_websocket_server(**ws_kwargs):
    import websockets.sync.server
    wsd = websockets.sync.server.serve(
        websocket_handler, '127.0.0.1', 0,
        process_request=process_request, open_timeout=2, **ws_kwargs)
    ws_port = wsd.socket.getsockname()[1]
    ws_server_thread = threading.Thread(target=wsd.serve_forever)
    ws_server_thread.daemon = True
    ws_server_thread.start()
    return ws_server_thread, ws_port


def create_ws_websocket_server():
    return create_websocket_server()


def create_wss_websocket_server():
    certfn = os.path.join(TEST_DIR, 'testcert.pem')
    sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sslctx.load_cert_chain(certfn, None)
    return create_websocket_server(ssl_context=sslctx)


MTLS_CERT_DIR = os.path.join(TEST_DIR, 'testdata', 'certificate')


def create_mtls_wss_websocket_server():
    certfn = os.path.join(TEST_DIR, 'testcert.pem')
    cacertfn = os.path.join(MTLS_CERT_DIR, 'ca.crt')

    sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sslctx.verify_mode = ssl.CERT_REQUIRED
    sslctx.load_verify_locations(cafile=cacertfn)
    sslctx.load_cert_chain(certfn, None)

    return create_websocket_server(ssl_context=sslctx)


def create_legacy_wss_websocket_server():
    certfn = os.path.join(TEST_DIR, 'testcert.pem')
    sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sslctx.maximum_version = ssl.TLSVersion.TLSv1_2
    sslctx.set_ciphers('SHA1:AESCCM:aDSS:eNULL:aNULL')
    sslctx.load_cert_chain(certfn, None)
    return create_websocket_server(ssl_context=sslctx)


def ws_validate_and_send(rh, req):
    rh.validate(req)
    max_tries = 3
    for i in range(max_tries):
        try:
            return rh.send(req)
        except TransportError as e:
            if i < (max_tries - 1) and 'connection closed during handshake' in str(e):
                # websockets server sometimes hangs on new connections
                continue
            raise


@pytest.mark.skipif(not websockets, reason='websockets must be installed to test websocket request handlers')
@pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
class TestWebsSocketRequestHandlerConformance:
    @classmethod
    def setup_class(cls):
        cls.ws_thread, cls.ws_port = create_ws_websocket_server()
        cls.ws_base_url = f'ws://127.0.0.1:{cls.ws_port}'

        cls.wss_thread, cls.wss_port = create_wss_websocket_server()
        cls.wss_base_url = f'wss://127.0.0.1:{cls.wss_port}'

        cls.bad_wss_thread, cls.bad_wss_port = create_websocket_server(ssl_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER))
        cls.bad_wss_host = f'wss://127.0.0.1:{cls.bad_wss_port}'

        cls.mtls_wss_thread, cls.mtls_wss_port = create_mtls_wss_websocket_server()
        cls.mtls_wss_base_url = f'wss://127.0.0.1:{cls.mtls_wss_port}'

        cls.legacy_wss_thread, cls.legacy_wss_port = create_legacy_wss_websocket_server()
        cls.legacy_wss_host = f'wss://127.0.0.1:{cls.legacy_wss_port}'

    def test_basic_websockets(self, handler):
        with handler() as rh:
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            assert 'upgrade' in ws.headers
            assert ws.status == 101
            ws.send('foo')
            assert ws.recv() == 'foo'
            ws.close()

    # https://www.rfc-editor.org/rfc/rfc6455.html#section-5.6
    @pytest.mark.parametrize('msg,opcode', [('str', 1), (b'bytes', 2)])
    def test_send_types(self, handler, msg, opcode):
        with handler() as rh:
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            ws.send(msg)
            assert int(ws.recv()) == opcode
            ws.close()

    def test_verify_cert(self, handler):
        with handler() as rh:
            with pytest.raises(CertificateVerifyError):
                ws_validate_and_send(rh, Request(self.wss_base_url))

        with handler(verify=False) as rh:
            ws = ws_validate_and_send(rh, Request(self.wss_base_url))
            assert ws.status == 101
            ws.close()

    def test_ssl_error(self, handler):
        with handler(verify=False) as rh:
            with pytest.raises(SSLError, match=r'ssl(?:v3|/tls) alert handshake failure') as exc_info:
                ws_validate_and_send(rh, Request(self.bad_wss_host))
            assert not issubclass(exc_info.type, CertificateVerifyError)

    def test_legacy_ssl_extension(self, handler):
        with handler(verify=False) as rh:
            ws = ws_validate_and_send(rh, Request(self.legacy_wss_host, extensions={'legacy_ssl': True}))
            assert ws.status == 101
            ws.close()

            # Ensure only applies to request extension
            with pytest.raises(SSLError):
                ws_validate_and_send(rh, Request(self.legacy_wss_host))

    def test_legacy_ssl_support(self, handler):
        with handler(verify=False, legacy_ssl_support=True) as rh:
            ws = ws_validate_and_send(rh, Request(self.legacy_wss_host))
            assert ws.status == 101
            ws.close()

    @pytest.mark.parametrize('path,expected', [
        # Unicode characters should be encoded with uppercase percent-encoding
        ('/中文', '/%E4%B8%AD%E6%96%87'),
        # don't normalize existing percent encodings
        ('/%c7%9f', '/%c7%9f'),
    ])
    def test_percent_encode(self, handler, path, expected):
        with handler() as rh:
            ws = ws_validate_and_send(rh, Request(f'{self.ws_base_url}{path}'))
            ws.send('path')
            assert ws.recv() == expected
            assert ws.status == 101
            ws.close()

    def test_remove_dot_segments(self, handler):
        with handler() as rh:
            # This isn't a comprehensive test,
            # but it should be enough to check whether the handler is removing dot segments
            ws = ws_validate_and_send(rh, Request(f'{self.ws_base_url}/a/b/./../../test'))
            assert ws.status == 101
            ws.send('path')
            assert ws.recv() == '/test'
            ws.close()

    # We are restricted to known HTTP status codes in http.HTTPStatus
    # Redirects are not supported for websockets
    @pytest.mark.parametrize('status', (200, 204, 301, 302, 303, 400, 500, 511))
    def test_raise_http_error(self, handler, status):
        with handler() as rh:
            with pytest.raises(HTTPError) as exc_info:
                ws_validate_and_send(rh, Request(f'{self.ws_base_url}/gen_{status}'))
            assert exc_info.value.status == status

    @pytest.mark.parametrize('params,extensions', [
        ({'timeout': sys.float_info.min}, {}),
        ({}, {'timeout': sys.float_info.min}),
    ])
    def test_read_timeout(self, handler, params, extensions):
        with handler(**params) as rh:
            with pytest.raises(TransportError):
                ws_validate_and_send(rh, Request(self.ws_base_url, extensions=extensions))

    def test_connect_timeout(self, handler):
        # nothing should be listening on this port
        connect_timeout_url = 'ws://10.255.255.255'
        with handler(timeout=0.01) as rh, pytest.raises(TransportError):
            now = time.time()
            ws_validate_and_send(rh, Request(connect_timeout_url))
        assert time.time() - now < DEFAULT_TIMEOUT

        # Per request timeout, should override handler timeout
        request = Request(connect_timeout_url, extensions={'timeout': 0.01})
        with handler() as rh, pytest.raises(TransportError):
            now = time.time()
            ws_validate_and_send(rh, request)
        assert time.time() - now < DEFAULT_TIMEOUT

    def test_cookies(self, handler):
        cookiejar = YoutubeDLCookieJar()
        cookiejar.set_cookie(http.cookiejar.Cookie(
            version=0, name='test', value='ytdlp', port=None, port_specified=False,
            domain='127.0.0.1', domain_specified=True, domain_initial_dot=False, path='/',
            path_specified=True, secure=False, expires=None, discard=False, comment=None,
            comment_url=None, rest={}))

        with handler(cookiejar=cookiejar) as rh:
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            assert json.loads(ws.recv())['cookie'] == 'test=ytdlp'
            ws.close()

        with handler() as rh:
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            assert 'cookie' not in json.loads(ws.recv())
            ws.close()

            ws = ws_validate_and_send(rh, Request(self.ws_base_url, extensions={'cookiejar': cookiejar}))
            ws.send('headers')
            assert json.loads(ws.recv())['cookie'] == 'test=ytdlp'
            ws.close()

    @pytest.mark.skip_handler('Websockets', 'Set-Cookie not supported by websockets')
    def test_cookie_sync_only_cookiejar(self, handler):
        # Ensure that cookies are ONLY being handled by the cookiejar
        with handler() as rh:
            ws_validate_and_send(rh, Request(f'{self.ws_base_url}/get_cookie', extensions={'cookiejar': YoutubeDLCookieJar()}))
            ws = ws_validate_and_send(rh, Request(self.ws_base_url, extensions={'cookiejar': YoutubeDLCookieJar()}))
            ws.send('headers')
            assert 'cookie' not in json.loads(ws.recv())
            ws.close()

    @pytest.mark.skip_handler('Websockets', 'Set-Cookie not supported by websockets')
    def test_cookie_sync_delete_cookie(self, handler):
        # Ensure that cookies are ONLY being handled by the cookiejar
        cookiejar = YoutubeDLCookieJar()
        with handler(verbose=True, cookiejar=cookiejar) as rh:
            ws_validate_and_send(rh, Request(f'{self.ws_base_url}/get_cookie'))
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            assert json.loads(ws.recv())['cookie'] == 'test=ytdlp'
            ws.close()
            cookiejar.clear_session_cookies()
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            assert 'cookie' not in json.loads(ws.recv())
            ws.close()

    def test_source_address(self, handler):
        source_address = f'127.0.0.{random.randint(5, 255)}'
        verify_address_availability(source_address)
        with handler(source_address=source_address) as rh:
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            ws.send('source_address')
            assert source_address == ws.recv()
            ws.close()

    def test_response_url(self, handler):
        with handler() as rh:
            url = f'{self.ws_base_url}/something'
            ws = ws_validate_and_send(rh, Request(url))
            assert ws.url == url
            ws.close()

    def test_request_headers(self, handler):
        with handler(headers=HTTPHeaderDict({'test1': 'test', 'test2': 'test2'})) as rh:
            # Global Headers
            ws = ws_validate_and_send(rh, Request(self.ws_base_url))
            ws.send('headers')
            headers = HTTPHeaderDict(json.loads(ws.recv()))
            assert headers['test1'] == 'test'
            ws.close()

            # Per request headers, merged with global
            ws = ws_validate_and_send(rh, Request(
                self.ws_base_url, headers={'test2': 'changed', 'test3': 'test3'}))
            ws.send('headers')
            headers = HTTPHeaderDict(json.loads(ws.recv()))
            assert headers['test1'] == 'test'
            assert headers['test2'] == 'changed'
            assert headers['test3'] == 'test3'
            ws.close()

    @pytest.mark.parametrize('client_cert', (
        {'client_certificate': os.path.join(MTLS_CERT_DIR, 'clientwithkey.crt')},
        {
            'client_certificate': os.path.join(MTLS_CERT_DIR, 'client.crt'),
            'client_certificate_key': os.path.join(MTLS_CERT_DIR, 'client.key'),
        },
        {
            'client_certificate': os.path.join(MTLS_CERT_DIR, 'clientwithencryptedkey.crt'),
            'client_certificate_password': 'foobar',
        },
        {
            'client_certificate': os.path.join(MTLS_CERT_DIR, 'client.crt'),
            'client_certificate_key': os.path.join(MTLS_CERT_DIR, 'clientencrypted.key'),
            'client_certificate_password': 'foobar',
        },
    ))
    def test_mtls(self, handler, client_cert):
        with handler(
            # Disable client-side validation of unacceptable self-signed testcert.pem
            # The test is of a check on the server side, so unaffected
            verify=False,
            client_cert=client_cert,
        ) as rh:
            ws_validate_and_send(rh, Request(self.mtls_wss_base_url)).close()

    def test_request_disable_proxy(self, handler):
        for proxy_proto in handler._SUPPORTED_PROXY_SCHEMES or ['ws']:
            # Given handler is configured with a proxy
            with handler(proxies={'ws': f'{proxy_proto}://10.255.255.255'}, timeout=5) as rh:
                # When a proxy is explicitly set to None for the request
                ws = ws_validate_and_send(rh, Request(self.ws_base_url, proxies={'http': None}))
                # Then no proxy should be used
                assert ws.status == 101
                ws.close()

    @pytest.mark.skip_handlers_if(
        lambda _, handler: Features.NO_PROXY not in handler._SUPPORTED_FEATURES, 'handler does not support NO_PROXY')
    def test_noproxy(self, handler):
        for proxy_proto in handler._SUPPORTED_PROXY_SCHEMES or ['ws']:
            # Given the handler is configured with a proxy
            with handler(proxies={'ws': f'{proxy_proto}://10.255.255.255'}, timeout=5) as rh:
                for no_proxy in (f'127.0.0.1:{self.ws_port}', '127.0.0.1', 'localhost'):
                    # When request no proxy includes the request url host
                    ws = ws_validate_and_send(rh, Request(self.ws_base_url, proxies={'no': no_proxy}))
                    # Then the proxy should not be used
                    assert ws.status == 101
                    ws.close()

    @pytest.mark.skip_handlers_if(
        lambda _, handler: Features.ALL_PROXY not in handler._SUPPORTED_FEATURES, 'handler does not support ALL_PROXY')
    def test_allproxy(self, handler):
        supported_proto = traverse_obj(handler._SUPPORTED_PROXY_SCHEMES, 0, default='ws')
        # This is a bit of a hacky test, but it should be enough to check whether the handler is using the proxy.
        # 0.1s might not be enough of a timeout if proxy is not used in all cases, but should still get failures.
        with handler(proxies={'all': f'{supported_proto}://10.255.255.255'}, timeout=0.1) as rh:
            with pytest.raises(TransportError):
                ws_validate_and_send(rh, Request(self.ws_base_url)).close()

        with handler(timeout=0.1) as rh:
            with pytest.raises(TransportError):
                ws_validate_and_send(
                    rh, Request(self.ws_base_url, proxies={'all': f'{supported_proto}://10.255.255.255'})).close()


def create_fake_ws_connection(raised):
    import websockets.sync.client

    class FakeWsConnection(websockets.sync.client.ClientConnection):
        def __init__(self, *args, **kwargs):
            class FakeResponse:
                body = b''
                headers = {}
                status_code = 101
                reason_phrase = 'test'

            self.response = FakeResponse()

        def send(self, *args, **kwargs):
            raise raised()

        def recv(self, *args, **kwargs):
            raise raised()

        def close(self, *args, **kwargs):
            return

    return FakeWsConnection()


@pytest.mark.parametrize('handler', ['Websockets'], indirect=True)
class TestWebsocketsRequestHandler:
    @pytest.mark.parametrize('raised,expected', [
        # https://websockets.readthedocs.io/en/stable/reference/exceptions.html
        (lambda: websockets.exceptions.InvalidURI(msg='test', uri='test://'), RequestError),
        # Requires a response object. Should be covered by HTTP error tests.
        # (lambda: websockets.exceptions.InvalidStatus(), TransportError),
        (lambda: websockets.exceptions.InvalidHandshake(), TransportError),
        # These are subclasses of InvalidHandshake
        (lambda: websockets.exceptions.InvalidHeader(name='test'), TransportError),
        (lambda: websockets.exceptions.NegotiationError(), TransportError),
        # Catch-all
        (lambda: websockets.exceptions.WebSocketException(), TransportError),
        (lambda: TimeoutError(), TransportError),
        # These may be raised by our create_connection implementation, which should also be caught
        (lambda: OSError(), TransportError),
        (lambda: ssl.SSLError(), SSLError),
        (lambda: ssl.SSLCertVerificationError(), CertificateVerifyError),
        (lambda: socks.ProxyError(), ProxyError),
    ])
    def test_request_error_mapping(self, handler, monkeypatch, raised, expected):
        import websockets.sync.client

        import yt_dlp.networking._websockets
        with handler() as rh:
            def fake_connect(*args, **kwargs):
                raise raised()
            monkeypatch.setattr(yt_dlp.networking._websockets, 'create_connection', lambda *args, **kwargs: None)
            monkeypatch.setattr(websockets.sync.client, 'connect', fake_connect)
            with pytest.raises(expected) as exc_info:
                rh.send(Request('ws://fake-url'))
            assert exc_info.type is expected

    @pytest.mark.parametrize('raised,expected,match', [
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.send
        (lambda: websockets.exceptions.ConnectionClosed(None, None), TransportError, None),
        (lambda: RuntimeError(), TransportError, None),
        (lambda: TimeoutError(), TransportError, None),
        (lambda: TypeError(), RequestError, None),
        (lambda: socks.ProxyError(), ProxyError, None),
        # Catch-all
        (lambda: websockets.exceptions.WebSocketException(), TransportError, None),
    ])
    def test_ws_send_error_mapping(self, handler, monkeypatch, raised, expected, match):
        from yt_dlp.networking._websockets import WebsocketsResponseAdapter
        ws = WebsocketsResponseAdapter(create_fake_ws_connection(raised), url='ws://fake-url')
        with pytest.raises(expected, match=match) as exc_info:
            ws.send('test')
        assert exc_info.type is expected

    @pytest.mark.parametrize('raised,expected,match', [
        # https://websockets.readthedocs.io/en/stable/reference/sync/client.html#websockets.sync.client.ClientConnection.recv
        (lambda: websockets.exceptions.ConnectionClosed(None, None), TransportError, None),
        (lambda: RuntimeError(), TransportError, None),
        (lambda: TimeoutError(), TransportError, None),
        (lambda: socks.ProxyError(), ProxyError, None),
        # Catch-all
        (lambda: websockets.exceptions.WebSocketException(), TransportError, None),
    ])
    def test_ws_recv_error_mapping(self, handler, monkeypatch, raised, expected, match):
        from yt_dlp.networking._websockets import WebsocketsResponseAdapter
        ws = WebsocketsResponseAdapter(create_fake_ws_connection(raised), url='ws://fake-url')
        with pytest.raises(expected, match=match) as exc_info:
            ws.recv()
        assert exc_info.type is expected
