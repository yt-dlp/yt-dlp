#!/usr/bin/env python3

# Allow direct execution
import os
import sys

import pytest

from yt_dlp.networking.common import Features, DEFAULT_TIMEOUT

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gzip
import http.client
import http.cookiejar
import http.server
import io
import logging
import pathlib
import random
import ssl
import tempfile
import threading
import time
import urllib.error
import urllib.request
import warnings
import zlib
from email.message import Message
from http.cookiejar import CookieJar

from test.helper import (
    FakeYDL,
    http_server_port,
    validate_and_send,
    verify_address_availability,
)
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.dependencies import brotli, curl_cffi, requests, urllib3
from yt_dlp.networking import (
    HEADRequest,
    PUTRequest,
    Request,
    RequestDirector,
    RequestHandler,
    Response,
)
from yt_dlp.networking._urllib import UrllibRH
from yt_dlp.networking.exceptions import (
    CertificateVerifyError,
    HTTPError,
    IncompleteRead,
    NoSupportingHandlers,
    ProxyError,
    RequestError,
    SSLError,
    TransportError,
    UnsupportedRequest,
)
from yt_dlp.networking.impersonate import (
    ImpersonateRequestHandler,
    ImpersonateTarget,
)
from yt_dlp.utils import YoutubeDLError
from yt_dlp.utils._utils import _YDLLogger as FakeLogger
from yt_dlp.utils.networking import HTTPHeaderDict, std_headers

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class HTTPTestRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    default_request_version = 'HTTP/1.1'

    def log_message(self, format, *args):
        pass

    def _headers(self):
        payload = str(self.headers).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _redirect(self):
        self.send_response(int(self.path[len('/redirect_'):]))
        self.send_header('Location', '/method')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _method(self, method, payload=None):
        self.send_response(200)
        self.send_header('Content-Length', str(len(payload or '')))
        self.send_header('Method', method)
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _status(self, status):
        payload = f'<html>{status} NOT FOUND</html>'.encode()
        self.send_response(int(status))
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_data(self):
        if 'Content-Length' in self.headers:
            return self.rfile.read(int(self.headers['Content-Length']))
        else:
            return b''

    def do_POST(self):
        data = self._read_data() + str(self.headers).encode()
        if self.path.startswith('/redirect_'):
            self._redirect()
        elif self.path.startswith('/method'):
            self._method('POST', data)
        elif self.path.startswith('/headers'):
            self._headers()
        else:
            self._status(404)

    def do_HEAD(self):
        if self.path.startswith('/redirect_'):
            self._redirect()
        elif self.path.startswith('/method'):
            self._method('HEAD')
        else:
            self._status(404)

    def do_PUT(self):
        data = self._read_data() + str(self.headers).encode()
        if self.path.startswith('/redirect_'):
            self._redirect()
        elif self.path.startswith('/method'):
            self._method('PUT', data)
        else:
            self._status(404)

    def do_GET(self):
        if self.path == '/video.html':
            payload = b'<html><video src="/vid.mp4" /></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/vid.mp4':
            payload = b'\x00\x00\x00\x00\x20\x66\x74[video]'
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/%E4%B8%AD%E6%96%87.html':
            payload = b'<html><video src="/vid.mp4" /></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/%c7%9f':
            payload = b'<html><video src="/vid.mp4" /></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path.startswith('/redirect_loop'):
            self.send_response(301)
            self.send_header('Location', self.path)
            self.send_header('Content-Length', '0')
            self.end_headers()
        elif self.path == '/redirect_dotsegments':
            self.send_response(301)
            # redirect to /headers but with dot segments before
            self.send_header('Location', '/a/b/./../../headers')
            self.send_header('Content-Length', '0')
            self.end_headers()
        elif self.path == '/redirect_dotsegments_absolute':
            self.send_response(301)
            # redirect to /headers but with dot segments before - absolute url
            self.send_header('Location', f'http://127.0.0.1:{http_server_port(self.server)}/a/b/./../../headers')
            self.send_header('Content-Length', '0')
            self.end_headers()
        elif self.path.startswith('/redirect_'):
            self._redirect()
        elif self.path.startswith('/method'):
            self._method('GET', str(self.headers).encode())
        elif self.path.startswith('/headers'):
            self._headers()
        elif self.path.startswith('/308-to-headers'):
            self.send_response(308)
            # redirect to "localhost" for testing cookie redirection handling
            self.send_header('Location', f'http://localhost:{self.connection.getsockname()[1]}/headers')
            self.send_header('Content-Length', '0')
            self.end_headers()
        elif self.path == '/trailing_garbage':
            payload = b'<html><video src="/vid.mp4" /></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Encoding', 'gzip')
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode='wb') as f:
                f.write(payload)
            compressed = buf.getvalue() + b'trailing garbage'
            self.send_header('Content-Length', str(len(compressed)))
            self.end_headers()
            self.wfile.write(compressed)
        elif self.path == '/302-non-ascii-redirect':
            new_url = f'http://127.0.0.1:{http_server_port(self.server)}/中文.html'
            self.send_response(301)
            self.send_header('Location', new_url)
            self.send_header('Content-Length', '0')
            self.end_headers()
        elif self.path == '/content-encoding':
            encodings = self.headers.get('ytdl-encoding', '')
            payload = b'<html><video src="/vid.mp4" /></html>'
            for encoding in filter(None, (e.strip() for e in encodings.split(','))):
                if encoding == 'br' and brotli:
                    payload = brotli.compress(payload)
                elif encoding == 'gzip':
                    buf = io.BytesIO()
                    with gzip.GzipFile(fileobj=buf, mode='wb') as f:
                        f.write(payload)
                    payload = buf.getvalue()
                elif encoding == 'deflate':
                    payload = zlib.compress(payload)
                elif encoding == 'unsupported':
                    payload = b'raw'
                    break
                else:
                    self._status(415)
                    return
            self.send_response(200)
            self.send_header('Content-Encoding', encodings)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path.startswith('/gen_'):
            payload = b'<html></html>'
            self.send_response(int(self.path[len('/gen_'):]))
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path.startswith('/incompleteread'):
            payload = b'<html></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', '234234')
            self.end_headers()
            self.wfile.write(payload)
            self.finish()
        elif self.path.startswith('/timeout_'):
            time.sleep(int(self.path[len('/timeout_'):]))
            self._headers()
        elif self.path == '/source_address':
            payload = str(self.client_address[0]).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            self.finish()
        else:
            self._status(404)

    def send_header(self, keyword, value):
        """
        Forcibly allow HTTP server to send non percent-encoded non-ASCII characters in headers.
        This is against what is defined in RFC 3986, however we need to test we support this
        since some sites incorrectly do this.
        """
        if keyword.lower() == 'connection':
            return super().send_header(keyword, value)

        if not hasattr(self, '_headers_buffer'):
            self._headers_buffer = []

        self._headers_buffer.append(f'{keyword}: {value}\r\n'.encode())


class TestRequestHandlerBase:
    @classmethod
    def setup_class(cls):
        cls.http_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        cls.http_port = http_server_port(cls.http_httpd)
        cls.http_server_thread = threading.Thread(target=cls.http_httpd.serve_forever)
        # FIXME: we should probably stop the http server thread after each test
        # See: https://github.com/yt-dlp/yt-dlp/pull/7094#discussion_r1199746041
        cls.http_server_thread.daemon = True
        cls.http_server_thread.start()

        # HTTPS server
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        cls.https_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.load_cert_chain(certfn, None)
        cls.https_httpd.socket = sslctx.wrap_socket(cls.https_httpd.socket, server_side=True)
        cls.https_port = http_server_port(cls.https_httpd)
        cls.https_server_thread = threading.Thread(target=cls.https_httpd.serve_forever)
        cls.https_server_thread.daemon = True
        cls.https_server_thread.start()


@pytest.mark.parametrize('handler', ['Urllib', 'Requests', 'CurlCFFI'], indirect=True)
class TestHTTPRequestHandler(TestRequestHandlerBase):

    def test_verify_cert(self, handler):
        with handler() as rh:
            with pytest.raises(CertificateVerifyError):
                validate_and_send(rh, Request(f'https://127.0.0.1:{self.https_port}/headers'))

        with handler(verify=False) as rh:
            r = validate_and_send(rh, Request(f'https://127.0.0.1:{self.https_port}/headers'))
            assert r.status == 200
            r.close()

    def test_ssl_error(self, handler):
        # HTTPS server with too old TLS version
        # XXX: is there a better way to test this than to create a new server?
        https_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        https_httpd.socket = sslctx.wrap_socket(https_httpd.socket, server_side=True)
        https_port = http_server_port(https_httpd)
        https_server_thread = threading.Thread(target=https_httpd.serve_forever)
        https_server_thread.daemon = True
        https_server_thread.start()

        with handler(verify=False) as rh:
            with pytest.raises(SSLError, match=r'(?i)ssl(?:v3|/tls).alert.handshake.failure') as exc_info:
                validate_and_send(rh, Request(f'https://127.0.0.1:{https_port}/headers'))
            assert not issubclass(exc_info.type, CertificateVerifyError)

    def test_percent_encode(self, handler):
        with handler() as rh:
            # Unicode characters should be encoded with uppercase percent-encoding
            res = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/中文.html'))
            assert res.status == 200
            res.close()
            # don't normalize existing percent encodings
            res = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/%c7%9f'))
            assert res.status == 200
            res.close()

    @pytest.mark.parametrize('path', [
        '/a/b/./../../headers',
        '/redirect_dotsegments',
        # https://github.com/yt-dlp/yt-dlp/issues/9020
        '/redirect_dotsegments_absolute',
    ])
    def test_remove_dot_segments(self, handler, path):
        with handler(verbose=True) as rh:
            # This isn't a comprehensive test,
            # but it should be enough to check whether the handler is removing dot segments in required scenarios
            res = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}{path}'))
            assert res.status == 200
            assert res.url == f'http://127.0.0.1:{self.http_port}/headers'
            res.close()

    @pytest.mark.skip_handler('CurlCFFI', 'not supported by curl-cffi (non-standard)')
    def test_unicode_path_redirection(self, handler):
        with handler() as rh:
            r = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/302-non-ascii-redirect'))
            assert r.url == f'http://127.0.0.1:{self.http_port}/%E4%B8%AD%E6%96%87.html'
            r.close()

    def test_raise_http_error(self, handler):
        with handler() as rh:
            for bad_status in (400, 500, 599, 302):
                with pytest.raises(HTTPError):
                    validate_and_send(rh, Request('http://127.0.0.1:%d/gen_%d' % (self.http_port, bad_status)))

            # Should not raise an error
            validate_and_send(rh, Request('http://127.0.0.1:%d/gen_200' % self.http_port)).close()

    def test_response_url(self, handler):
        with handler() as rh:
            # Response url should be that of the last url in redirect chain
            res = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/redirect_301'))
            assert res.url == f'http://127.0.0.1:{self.http_port}/method'
            res.close()
            res2 = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/gen_200'))
            assert res2.url == f'http://127.0.0.1:{self.http_port}/gen_200'
            res2.close()

    # Covers some basic cases we expect some level of consistency between request handlers for
    @pytest.mark.parametrize('redirect_status,method,expected', [
        # A 303 must either use GET or HEAD for subsequent request
        (303, 'POST', ('', 'GET', False)),
        (303, 'HEAD', ('', 'HEAD', False)),

        # 301 and 302 turn POST only into a GET
        (301, 'POST', ('', 'GET', False)),
        (301, 'HEAD', ('', 'HEAD', False)),
        (302, 'POST', ('', 'GET', False)),
        (302, 'HEAD', ('', 'HEAD', False)),

        # 307 and 308 should not change method
        (307, 'POST', ('testdata', 'POST', True)),
        (308, 'POST', ('testdata', 'POST', True)),
        (307, 'HEAD', ('', 'HEAD', False)),
        (308, 'HEAD', ('', 'HEAD', False)),
    ])
    def test_redirect(self, handler, redirect_status, method, expected):
        with handler() as rh:
            data = b'testdata' if method == 'POST' else None
            headers = {}
            if data is not None:
                headers['Content-Type'] = 'application/test'
            res = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/redirect_{redirect_status}', method=method, data=data,
                            headers=headers))

            headers = b''
            data_recv = b''
            if data is not None:
                data_recv += res.read(len(data))
                if data_recv != data:
                    headers += data_recv
                    data_recv = b''

            headers += res.read()

            assert expected[0] == data_recv.decode()
            assert expected[1] == res.headers.get('method')
            assert expected[2] == ('content-length' in headers.decode().lower())

    def test_request_cookie_header(self, handler):
        # We should accept a Cookie header being passed as in normal headers and handle it appropriately.
        with handler() as rh:
            # Specified Cookie header should be used
            res = validate_and_send(
                rh, Request(
                    f'http://127.0.0.1:{self.http_port}/headers',
                    headers={'Cookie': 'test=test'})).read().decode()
            assert 'cookie: test=test' in res.lower()

            # Specified Cookie header should be removed on any redirect
            res = validate_and_send(
                rh, Request(
                    f'http://127.0.0.1:{self.http_port}/308-to-headers',
                    headers={'Cookie': 'test=test2'})).read().decode()
            assert 'cookie: test=test2' not in res.lower()

        # Specified Cookie header should override global cookiejar for that request
        # Whether cookies from the cookiejar is applied on the redirect is considered undefined for now
        cookiejar = YoutubeDLCookieJar()
        cookiejar.set_cookie(http.cookiejar.Cookie(
            version=0, name='test', value='ytdlp', port=None, port_specified=False,
            domain='127.0.0.1', domain_specified=True, domain_initial_dot=False, path='/',
            path_specified=True, secure=False, expires=None, discard=False, comment=None,
            comment_url=None, rest={}))

        with handler(cookiejar=cookiejar) as rh:
            data = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/headers', headers={'cookie': 'test=test3'})).read()
            assert b'cookie: test=ytdlp' not in data.lower()
            assert b'cookie: test=test3' in data.lower()

    def test_redirect_loop(self, handler):
        with handler() as rh:
            with pytest.raises(HTTPError, match='redirect loop'):
                validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/redirect_loop'))

    def test_incompleteread(self, handler):
        with handler(timeout=2) as rh:
            with pytest.raises(IncompleteRead, match='13 bytes read, 234221 more expected'):
                validate_and_send(rh, Request('http://127.0.0.1:%d/incompleteread' % self.http_port)).read()

    def test_cookies(self, handler):
        cookiejar = YoutubeDLCookieJar()
        cookiejar.set_cookie(http.cookiejar.Cookie(
            0, 'test', 'ytdlp', None, False, '127.0.0.1', True,
            False, '/headers', True, False, None, False, None, None, {}))

        with handler(cookiejar=cookiejar) as rh:
            data = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/headers')).read()
            assert b'cookie: test=ytdlp' in data.lower()

        # Per request
        with handler() as rh:
            data = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/headers', extensions={'cookiejar': cookiejar})).read()
            assert b'cookie: test=ytdlp' in data.lower()

    def test_headers(self, handler):

        with handler(headers=HTTPHeaderDict({'test1': 'test', 'test2': 'test2'})) as rh:
            # Global Headers
            data = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/headers')).read().lower()
            assert b'test1: test' in data

            # Per request headers, merged with global
            data = validate_and_send(rh, Request(
                f'http://127.0.0.1:{self.http_port}/headers', headers={'test2': 'changed', 'test3': 'test3'})).read().lower()
            assert b'test1: test' in data
            assert b'test2: changed' in data
            assert b'test2: test2' not in data
            assert b'test3: test3' in data

    def test_read_timeout(self, handler):
        with handler() as rh:
            # Default timeout is 20 seconds, so this should go through
            validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/timeout_1'))

        with handler(timeout=0.1) as rh:
            with pytest.raises(TransportError):
                validate_and_send(
                    rh, Request(f'http://127.0.0.1:{self.http_port}/timeout_5'))

            # Per request timeout, should override handler timeout
            validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/timeout_1', extensions={'timeout': 4}))

    def test_connect_timeout(self, handler):
        # nothing should be listening on this port
        connect_timeout_url = 'http://10.255.255.255'
        with handler(timeout=0.01) as rh, pytest.raises(TransportError):
            now = time.time()
            validate_and_send(rh, Request(connect_timeout_url))
        assert time.time() - now < DEFAULT_TIMEOUT

        # Per request timeout, should override handler timeout
        request = Request(connect_timeout_url, extensions={'timeout': 0.01})
        with handler() as rh, pytest.raises(TransportError):
            now = time.time()
            validate_and_send(rh, request)
        assert time.time() - now < DEFAULT_TIMEOUT

    def test_source_address(self, handler):
        source_address = f'127.0.0.{random.randint(5, 255)}'
        # on some systems these loopback addresses we need for testing may not be available
        # see: https://github.com/yt-dlp/yt-dlp/issues/8890
        verify_address_availability(source_address)
        with handler(source_address=source_address) as rh:
            data = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/source_address')).read().decode()
            assert source_address == data

    # Not supported by CurlCFFI
    @pytest.mark.skip_handler('CurlCFFI', 'not supported by curl-cffi')
    def test_gzip_trailing_garbage(self, handler):
        with handler() as rh:
            data = validate_and_send(rh, Request(f'http://localhost:{self.http_port}/trailing_garbage')).read().decode()
            assert data == '<html><video src="/vid.mp4" /></html>'

    @pytest.mark.skip_handler('CurlCFFI', 'not applicable to curl-cffi')
    @pytest.mark.skipif(not brotli, reason='brotli support is not installed')
    def test_brotli(self, handler):
        with handler() as rh:
            res = validate_and_send(
                rh, Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'br'}))
            assert res.headers.get('Content-Encoding') == 'br'
            assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    def test_deflate(self, handler):
        with handler() as rh:
            res = validate_and_send(
                rh, Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'deflate'}))
            assert res.headers.get('Content-Encoding') == 'deflate'
            assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    def test_gzip(self, handler):
        with handler() as rh:
            res = validate_and_send(
                rh, Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'gzip'}))
            assert res.headers.get('Content-Encoding') == 'gzip'
            assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    def test_multiple_encodings(self, handler):
        with handler() as rh:
            for pair in ('gzip,deflate', 'deflate, gzip', 'gzip, gzip', 'deflate, deflate'):
                res = validate_and_send(
                    rh, Request(
                        f'http://127.0.0.1:{self.http_port}/content-encoding',
                        headers={'ytdl-encoding': pair}))
                assert res.headers.get('Content-Encoding') == pair
                assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    @pytest.mark.skip_handler('CurlCFFI', 'not supported by curl-cffi')
    def test_unsupported_encoding(self, handler):
        with handler() as rh:
            res = validate_and_send(
                rh, Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'unsupported', 'Accept-Encoding': '*'}))
            assert res.headers.get('Content-Encoding') == 'unsupported'
            assert res.read() == b'raw'

    def test_read(self, handler):
        with handler() as rh:
            res = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/headers'))
            assert res.readable()
            assert res.read(1) == b'H'
            assert res.read(3) == b'ost'
            assert res.read().decode().endswith('\n\n')
            assert res.read() == b''

    def test_request_disable_proxy(self, handler):
        for proxy_proto in handler._SUPPORTED_PROXY_SCHEMES or ['http']:
            # Given the handler is configured with a proxy
            with handler(proxies={'http': f'{proxy_proto}://10.255.255.255'}, timeout=5) as rh:
                # When a proxy is explicitly set to None for the request
                res = validate_and_send(
                    rh, Request(f'http://127.0.0.1:{self.http_port}/headers', proxies={'http': None}))
                # Then no proxy should be used
                res.close()
                assert res.status == 200

    @pytest.mark.skip_handlers_if(
        lambda _, handler: Features.NO_PROXY not in handler._SUPPORTED_FEATURES, 'handler does not support NO_PROXY')
    def test_noproxy(self, handler):
        for proxy_proto in handler._SUPPORTED_PROXY_SCHEMES or ['http']:
            # Given the handler is configured with a proxy
            with handler(proxies={'http': f'{proxy_proto}://10.255.255.255'}, timeout=5) as rh:
                for no_proxy in (f'127.0.0.1:{self.http_port}', '127.0.0.1', 'localhost'):
                    # When request no proxy includes the request url host
                    nop_response = validate_and_send(
                        rh, Request(f'http://127.0.0.1:{self.http_port}/headers', proxies={'no': no_proxy}))
                    # Then the proxy should not be used
                    assert nop_response.status == 200
                    nop_response.close()

    @pytest.mark.skip_handlers_if(
        lambda _, handler: Features.ALL_PROXY not in handler._SUPPORTED_FEATURES, 'handler does not support ALL_PROXY')
    def test_allproxy(self, handler):
        # This is a bit of a hacky test, but it should be enough to check whether the handler is using the proxy.
        # 0.1s might not be enough of a timeout if proxy is not used in all cases, but should still get failures.
        with handler(proxies={'all': 'http://10.255.255.255'}, timeout=0.1) as rh:
            with pytest.raises(TransportError):
                validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/headers')).close()

        with handler(timeout=0.1) as rh:
            with pytest.raises(TransportError):
                validate_and_send(
                    rh, Request(
                        f'http://127.0.0.1:{self.http_port}/headers', proxies={'all': 'http://10.255.255.255'})).close()


@pytest.mark.parametrize('handler', ['Urllib', 'Requests', 'CurlCFFI'], indirect=True)
class TestClientCertificate:
    @classmethod
    def setup_class(cls):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        cls.certdir = os.path.join(TEST_DIR, 'testdata', 'certificate')
        cacertfn = os.path.join(cls.certdir, 'ca.crt')
        cls.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), HTTPTestRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.verify_mode = ssl.CERT_REQUIRED
        sslctx.load_verify_locations(cafile=cacertfn)
        sslctx.load_cert_chain(certfn, None)
        cls.httpd.socket = sslctx.wrap_socket(cls.httpd.socket, server_side=True)
        cls.port = http_server_port(cls.httpd)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    def _run_test(self, handler, **handler_kwargs):
        with handler(
            # Disable client-side validation of unacceptable self-signed testcert.pem
            # The test is of a check on the server side, so unaffected
            verify=False,
            **handler_kwargs,
        ) as rh:
            validate_and_send(rh, Request(f'https://127.0.0.1:{self.port}/video.html')).read().decode()

    def test_certificate_combined_nopass(self, handler):
        self._run_test(handler, client_cert={
            'client_certificate': os.path.join(self.certdir, 'clientwithkey.crt'),
        })

    def test_certificate_nocombined_nopass(self, handler):
        self._run_test(handler, client_cert={
            'client_certificate': os.path.join(self.certdir, 'client.crt'),
            'client_certificate_key': os.path.join(self.certdir, 'client.key'),
        })

    def test_certificate_combined_pass(self, handler):
        self._run_test(handler, client_cert={
            'client_certificate': os.path.join(self.certdir, 'clientwithencryptedkey.crt'),
            'client_certificate_password': 'foobar',
        })

    def test_certificate_nocombined_pass(self, handler):
        self._run_test(handler, client_cert={
            'client_certificate': os.path.join(self.certdir, 'client.crt'),
            'client_certificate_key': os.path.join(self.certdir, 'clientencrypted.key'),
            'client_certificate_password': 'foobar',
        })


@pytest.mark.parametrize('handler', ['CurlCFFI'], indirect=True)
class TestHTTPImpersonateRequestHandler(TestRequestHandlerBase):
    def test_supported_impersonate_targets(self, handler):
        with handler(headers=std_headers) as rh:
            # note: this assumes the impersonate request handler supports the impersonate extension
            for target in rh.supported_targets:
                res = validate_and_send(rh, Request(
                    f'http://127.0.0.1:{self.http_port}/headers', extensions={'impersonate': target}))
                assert res.status == 200
                assert std_headers['user-agent'].lower() not in res.read().decode().lower()

    def test_response_extensions(self, handler):
        with handler() as rh:
            for target in rh.supported_targets:
                request = Request(
                    f'http://127.0.0.1:{self.http_port}/gen_200', extensions={'impersonate': target})
                res = validate_and_send(rh, request)
                assert res.extensions['impersonate'] == rh._get_request_target(request)

    def test_http_error_response_extensions(self, handler):
        with handler() as rh:
            for target in rh.supported_targets:
                request = Request(
                    f'http://127.0.0.1:{self.http_port}/gen_404', extensions={'impersonate': target})
                try:
                    validate_and_send(rh, request)
                except HTTPError as e:
                    res = e.response
                assert res.extensions['impersonate'] == rh._get_request_target(request)


class TestRequestHandlerMisc:
    """Misc generic tests for request handlers, not related to request or validation testing"""
    @pytest.mark.parametrize('handler,logger_name', [
        ('Requests', 'urllib3'),
        ('Websockets', 'websockets.client'),
        ('Websockets', 'websockets.server')
    ], indirect=['handler'])
    def test_remove_logging_handler(self, handler, logger_name):
        # Ensure any logging handlers, which may contain a YoutubeDL instance,
        # are removed when we close the request handler
        # See: https://github.com/yt-dlp/yt-dlp/issues/8922
        logging_handlers = logging.getLogger(logger_name).handlers
        before_count = len(logging_handlers)
        rh = handler()
        assert len(logging_handlers) == before_count + 1
        rh.close()
        assert len(logging_handlers) == before_count


@pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
class TestUrllibRequestHandler(TestRequestHandlerBase):
    def test_file_urls(self, handler):
        # See https://github.com/ytdl-org/youtube-dl/issues/8227
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.write(b'foobar')
        tf.close()
        req = Request(pathlib.Path(tf.name).as_uri())
        with handler() as rh:
            with pytest.raises(UnsupportedRequest):
                rh.validate(req)

            # Test that urllib never loaded FileHandler
            with pytest.raises(TransportError):
                rh.send(req)

        with handler(enable_file_urls=True) as rh:
            res = validate_and_send(rh, req)
            assert res.read() == b'foobar'
            res.close()

        os.unlink(tf.name)

    def test_http_error_returns_content(self, handler):
        # urllib HTTPError will try close the underlying response if reference to the HTTPError object is lost
        def get_response():
            with handler() as rh:
                # headers url
                try:
                    validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/gen_404'))
                except HTTPError as e:
                    return e.response

        assert get_response().read() == b'<html></html>'

    def test_verify_cert_error_text(self, handler):
        # Check the output of the error message
        with handler() as rh:
            with pytest.raises(
                CertificateVerifyError,
                match=r'\[SSL: CERTIFICATE_VERIFY_FAILED\] certificate verify failed: self.signed certificate'
            ):
                validate_and_send(rh, Request(f'https://127.0.0.1:{self.https_port}/headers'))

    @pytest.mark.parametrize('req,match,version_check', [
        # https://github.com/python/cpython/blob/987b712b4aeeece336eed24fcc87a950a756c3e2/Lib/http/client.py#L1256
        # bpo-39603: Check implemented in 3.7.9+, 3.8.5+
        (
            Request('http://127.0.0.1', method='GET\n'),
            'method can\'t contain control characters',
            lambda v: v < (3, 7, 9) or (3, 8, 0) <= v < (3, 8, 5)
        ),
        # https://github.com/python/cpython/blob/987b712b4aeeece336eed24fcc87a950a756c3e2/Lib/http/client.py#L1265
        # bpo-38576: Check implemented in 3.7.8+, 3.8.3+
        (
            Request('http://127.0.0. 1', method='GET'),
            'URL can\'t contain control characters',
            lambda v: v < (3, 7, 8) or (3, 8, 0) <= v < (3, 8, 3)
        ),
        # https://github.com/python/cpython/blob/987b712b4aeeece336eed24fcc87a950a756c3e2/Lib/http/client.py#L1288C31-L1288C50
        (Request('http://127.0.0.1', headers={'foo\n': 'bar'}), 'Invalid header name', None),
    ])
    def test_httplib_validation_errors(self, handler, req, match, version_check):
        if version_check and version_check(sys.version_info):
            pytest.skip(f'Python {sys.version} version does not have the required validation for this test.')

        with handler() as rh:
            with pytest.raises(RequestError, match=match) as exc_info:
                validate_and_send(rh, req)
            assert not isinstance(exc_info.value, TransportError)


@pytest.mark.parametrize('handler', ['Requests'], indirect=True)
class TestRequestsRequestHandler(TestRequestHandlerBase):
    @pytest.mark.parametrize('raised,expected', [
        (lambda: requests.exceptions.ConnectTimeout(), TransportError),
        (lambda: requests.exceptions.ReadTimeout(), TransportError),
        (lambda: requests.exceptions.Timeout(), TransportError),
        (lambda: requests.exceptions.ConnectionError(), TransportError),
        (lambda: requests.exceptions.ProxyError(), ProxyError),
        (lambda: requests.exceptions.SSLError('12[CERTIFICATE_VERIFY_FAILED]34'), CertificateVerifyError),
        (lambda: requests.exceptions.SSLError(), SSLError),
        (lambda: requests.exceptions.InvalidURL(), RequestError),
        (lambda: requests.exceptions.InvalidHeader(), RequestError),
        # catch-all: https://github.com/psf/requests/blob/main/src/requests/adapters.py#L535
        (lambda: urllib3.exceptions.HTTPError(), TransportError),
        (lambda: requests.exceptions.RequestException(), RequestError)
        #  (lambda: requests.exceptions.TooManyRedirects(), HTTPError) - Needs a response object
    ])
    def test_request_error_mapping(self, handler, monkeypatch, raised, expected):
        with handler() as rh:
            def mock_get_instance(*args, **kwargs):
                class MockSession:
                    def request(self, *args, **kwargs):
                        raise raised()
                return MockSession()

            monkeypatch.setattr(rh, '_get_instance', mock_get_instance)

            with pytest.raises(expected) as exc_info:
                rh.send(Request('http://fake'))

            assert exc_info.type is expected

    @pytest.mark.parametrize('raised,expected,match', [
        (lambda: urllib3.exceptions.SSLError(), SSLError, None),
        (lambda: urllib3.exceptions.TimeoutError(), TransportError, None),
        (lambda: urllib3.exceptions.ReadTimeoutError(None, None, None), TransportError, None),
        (lambda: urllib3.exceptions.ProtocolError(), TransportError, None),
        (lambda: urllib3.exceptions.DecodeError(), TransportError, None),
        (lambda: urllib3.exceptions.HTTPError(), TransportError, None),  # catch-all
        (
            lambda: urllib3.exceptions.ProtocolError('error', http.client.IncompleteRead(partial=b'abc', expected=4)),
            IncompleteRead,
            '3 bytes read, 4 more expected'
        ),
        (
            lambda: urllib3.exceptions.ProtocolError('error', urllib3.exceptions.IncompleteRead(partial=3, expected=5)),
            IncompleteRead,
            '3 bytes read, 5 more expected'
        ),
    ])
    def test_response_error_mapping(self, handler, monkeypatch, raised, expected, match):
        from requests.models import Response as RequestsResponse
        from urllib3.response import HTTPResponse as Urllib3Response

        from yt_dlp.networking._requests import RequestsResponseAdapter
        requests_res = RequestsResponse()
        requests_res.raw = Urllib3Response(body=b'', status=200)
        res = RequestsResponseAdapter(requests_res)

        def mock_read(*args, **kwargs):
            raise raised()
        monkeypatch.setattr(res.fp, 'read', mock_read)

        with pytest.raises(expected, match=match) as exc_info:
            res.read()

        assert exc_info.type is expected

    def test_close(self, handler, monkeypatch):
        rh = handler()
        session = rh._get_instance(cookiejar=rh.cookiejar)
        called = False
        original_close = session.close

        def mock_close(*args, **kwargs):
            nonlocal called
            called = True
            return original_close(*args, **kwargs)

        monkeypatch.setattr(session, 'close', mock_close)
        rh.close()
        assert called


@pytest.mark.parametrize('handler', ['CurlCFFI'], indirect=True)
class TestCurlCFFIRequestHandler(TestRequestHandlerBase):

    @pytest.mark.parametrize('params,extensions', [
        ({}, {'impersonate': ImpersonateTarget('chrome')}),
        ({'impersonate': ImpersonateTarget('chrome', '110')}, {}),
        ({'impersonate': ImpersonateTarget('chrome', '99')}, {'impersonate': ImpersonateTarget('chrome', '110')}),
    ])
    def test_impersonate(self, handler, params, extensions):
        with handler(headers=std_headers, **params) as rh:
            res = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/headers', extensions=extensions)).read().decode()
            assert 'sec-ch-ua: "Chromium";v="110"' in res
            # Check that user agent is added over ours
            assert 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36' in res

    def test_headers(self, handler):
        with handler(headers=std_headers) as rh:
            # Ensure curl-impersonate overrides our standard headers (usually added
            res = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/headers', extensions={
                    'impersonate': ImpersonateTarget('safari')}, headers={'x-custom': 'test', 'sec-fetch-mode': 'custom'})).read().decode().lower()

            assert std_headers['user-agent'].lower() not in res
            assert std_headers['accept-language'].lower() not in res
            assert std_headers['sec-fetch-mode'].lower() not in res
            # other than UA, custom headers that differ from std_headers should be kept
            assert 'sec-fetch-mode: custom' in res
            assert 'x-custom: test' in res
            # but when not impersonating don't remove std_headers
            res = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/headers', headers={'x-custom': 'test'})).read().decode().lower()
            # std_headers should be present
            for k, v in std_headers.items():
                assert f'{k}: {v}'.lower() in res

    @pytest.mark.parametrize('raised,expected,match', [
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.PARTIAL_FILE), IncompleteRead, None),
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.OPERATION_TIMEDOUT), TransportError, None),
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.RECV_ERROR), TransportError, None),
    ])
    def test_response_error_mapping(self, handler, monkeypatch, raised, expected, match):
        import curl_cffi.requests

        from yt_dlp.networking._curlcffi import CurlCFFIResponseAdapter
        curl_res = curl_cffi.requests.Response()
        res = CurlCFFIResponseAdapter(curl_res)

        def mock_read(*args, **kwargs):
            try:
                raise raised()
            except Exception as e:
                e.response = curl_res
                raise
        monkeypatch.setattr(res.fp, 'read', mock_read)

        with pytest.raises(expected, match=match) as exc_info:
            res.read()

        assert exc_info.type is expected

    @pytest.mark.parametrize('raised,expected,match', [
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.OPERATION_TIMEDOUT), TransportError, None),
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.PEER_FAILED_VERIFICATION), CertificateVerifyError, None),
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.SSL_CONNECT_ERROR), SSLError, None),
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.TOO_MANY_REDIRECTS), HTTPError, None),
        (lambda: curl_cffi.requests.errors.RequestsError(
            '', code=curl_cffi.const.CurlECode.PROXY), ProxyError, None),
    ])
    def test_request_error_mapping(self, handler, monkeypatch, raised, expected, match):
        import curl_cffi.requests
        curl_res = curl_cffi.requests.Response()
        curl_res.status_code = 301

        with handler() as rh:
            original_get_instance = rh._get_instance

            def mock_get_instance(*args, **kwargs):
                instance = original_get_instance(*args, **kwargs)

                def request(*_, **__):
                    try:
                        raise raised()
                    except Exception as e:
                        e.response = curl_res
                        raise
                monkeypatch.setattr(instance, 'request', request)
                return instance

            monkeypatch.setattr(rh, '_get_instance', mock_get_instance)

            with pytest.raises(expected) as exc_info:
                rh.send(Request('http://fake'))

            assert exc_info.type is expected

    def test_response_reader(self, handler):
        class FakeResponse:
            def __init__(self, raise_error=False):
                self.raise_error = raise_error
                self.closed = False

            def iter_content(self):
                yield b'foo'
                yield b'bar'
                yield b'z'
                if self.raise_error:
                    raise Exception('test')

            def close(self):
                self.closed = True

        from yt_dlp.networking._curlcffi import CurlCFFIResponseReader

        res = CurlCFFIResponseReader(FakeResponse())
        assert res.readable
        assert res.bytes_read == 0
        assert res.read(1) == b'f'
        assert res.bytes_read == 3
        assert res._buffer == b'oo'

        assert res.read(2) == b'oo'
        assert res.bytes_read == 3
        assert res._buffer == b''

        assert res.read(2) == b'ba'
        assert res.bytes_read == 6
        assert res._buffer == b'r'

        assert res.read(3) == b'rz'
        assert res.bytes_read == 7
        assert res._buffer == b''
        assert res.closed
        assert res._response.closed

        # should handle no size param
        res2 = CurlCFFIResponseReader(FakeResponse())
        assert res2.read() == b'foobarz'
        assert res2.bytes_read == 7
        assert res2._buffer == b''
        assert res2.closed

        # should close on an exception
        res3 = CurlCFFIResponseReader(FakeResponse(raise_error=True))
        with pytest.raises(Exception, match='test'):
            res3.read()
        assert res3._buffer == b''
        assert res3.bytes_read == 7
        assert res3.closed

        # buffer should be cleared on close
        res4 = CurlCFFIResponseReader(FakeResponse())
        res4.read(2)
        assert res4._buffer == b'o'
        res4.close()
        assert res4.closed
        assert res4._buffer == b''


def run_validation(handler, error, req, **handler_kwargs):
    with handler(**handler_kwargs) as rh:
        if error:
            with pytest.raises(error):
                rh.validate(req)
        else:
            rh.validate(req)


class TestRequestHandlerValidation:

    class ValidationRH(RequestHandler):
        def _send(self, request):
            raise RequestError('test')

    class NoCheckRH(ValidationRH):
        _SUPPORTED_FEATURES = None
        _SUPPORTED_PROXY_SCHEMES = None
        _SUPPORTED_URL_SCHEMES = None

        def _check_extensions(self, extensions):
            extensions.clear()

    class HTTPSupportedRH(ValidationRH):
        _SUPPORTED_URL_SCHEMES = ('http',)

    URL_SCHEME_TESTS = [
        # scheme, expected to fail, handler kwargs
        ('Urllib', [
            ('http', False, {}),
            ('https', False, {}),
            ('data', False, {}),
            ('ftp', False, {}),
            ('file', UnsupportedRequest, {}),
            ('file', False, {'enable_file_urls': True}),
        ]),
        ('Requests', [
            ('http', False, {}),
            ('https', False, {}),
        ]),
        ('Websockets', [
            ('ws', False, {}),
            ('wss', False, {}),
        ]),
        ('CurlCFFI', [
            ('http', False, {}),
            ('https', False, {}),
        ]),
        (NoCheckRH, [('http', False, {})]),
        (ValidationRH, [('http', UnsupportedRequest, {})])
    ]

    PROXY_SCHEME_TESTS = [
        # proxy scheme, expected to fail
        ('Urllib', 'http', [
            ('http', False),
            ('https', UnsupportedRequest),
            ('socks4', False),
            ('socks4a', False),
            ('socks5', False),
            ('socks5h', False),
            ('socks', UnsupportedRequest),
        ]),
        ('Requests', 'http', [
            ('http', False),
            ('https', False),
            ('socks4', False),
            ('socks4a', False),
            ('socks5', False),
            ('socks5h', False),
        ]),
        ('CurlCFFI', 'http', [
            ('http', False),
            ('https', False),
            ('socks4', False),
            ('socks4a', False),
            ('socks5', False),
            ('socks5h', False),
        ]),
        ('Websockets', 'ws', [
            ('http', UnsupportedRequest),
            ('https', UnsupportedRequest),
            ('socks4', False),
            ('socks4a', False),
            ('socks5', False),
            ('socks5h', False),
        ]),
        (NoCheckRH, 'http', [('http', False)]),
        (HTTPSupportedRH, 'http', [('http', UnsupportedRequest)]),
        (NoCheckRH, 'http', [('http', False)]),
        (HTTPSupportedRH, 'http', [('http', UnsupportedRequest)]),
    ]

    PROXY_KEY_TESTS = [
        # proxy key, proxy scheme, expected to fail
        ('Urllib', 'http', [
            ('all', 'http', False),
            ('unrelated', 'http', False),
        ]),
        ('Requests', 'http', [
            ('all', 'http', False),
            ('unrelated', 'http', False),
        ]),
        ('CurlCFFI', 'http', [
            ('all', 'http', False),
            ('unrelated', 'http', False),
        ]),
        ('Websockets', 'ws', [
            ('all', 'socks5', False),
            ('unrelated', 'socks5', False),
        ]),
        (NoCheckRH, 'http', [('all', 'http', False)]),
        (HTTPSupportedRH, 'http', [('all', 'http', UnsupportedRequest)]),
        (HTTPSupportedRH, 'http', [('no', 'http', UnsupportedRequest)]),
    ]

    EXTENSION_TESTS = [
        ('Urllib', 'http', [
            ({'cookiejar': 'notacookiejar'}, AssertionError),
            ({'cookiejar': YoutubeDLCookieJar()}, False),
            ({'cookiejar': CookieJar()}, AssertionError),
            ({'timeout': 1}, False),
            ({'timeout': 'notatimeout'}, AssertionError),
            ({'unsupported': 'value'}, UnsupportedRequest),
        ]),
        ('Requests', 'http', [
            ({'cookiejar': 'notacookiejar'}, AssertionError),
            ({'cookiejar': YoutubeDLCookieJar()}, False),
            ({'timeout': 1}, False),
            ({'timeout': 'notatimeout'}, AssertionError),
            ({'unsupported': 'value'}, UnsupportedRequest),
        ]),
        ('CurlCFFI', 'http', [
            ({'cookiejar': 'notacookiejar'}, AssertionError),
            ({'cookiejar': YoutubeDLCookieJar()}, False),
            ({'timeout': 1}, False),
            ({'timeout': 'notatimeout'}, AssertionError),
            ({'unsupported': 'value'}, UnsupportedRequest),
            ({'impersonate': ImpersonateTarget('badtarget', None, None, None)}, UnsupportedRequest),
            ({'impersonate': 123}, AssertionError),
            ({'impersonate': ImpersonateTarget('chrome', None, None, None)}, False),
            ({'impersonate': ImpersonateTarget(None, None, None, None)}, False),
            ({'impersonate': ImpersonateTarget()}, False),
            ({'impersonate': 'chrome'}, AssertionError)
        ]),
        (NoCheckRH, 'http', [
            ({'cookiejar': 'notacookiejar'}, False),
            ({'somerandom': 'test'}, False),  # but any extension is allowed through
        ]),
        ('Websockets', 'ws', [
            ({'cookiejar': YoutubeDLCookieJar()}, False),
            ({'timeout': 2}, False),
        ]),
    ]

    @pytest.mark.parametrize('handler,fail,scheme', [
        ('Urllib', False, 'http'),
        ('Requests', False, 'http'),
        ('CurlCFFI', False, 'http'),
        ('Websockets', False, 'ws')
    ], indirect=['handler'])
    def test_no_proxy(self, handler, fail, scheme):
        run_validation(handler, fail, Request(f'{scheme}://', proxies={'no': '127.0.0.1,github.com'}))
        run_validation(handler, fail, Request(f'{scheme}://'), proxies={'no': '127.0.0.1,github.com'})

    @pytest.mark.parametrize('handler,scheme', [
        ('Urllib', 'http'),
        (HTTPSupportedRH, 'http'),
        ('Requests', 'http'),
        ('CurlCFFI', 'http'),
        ('Websockets', 'ws')
    ], indirect=['handler'])
    def test_empty_proxy(self, handler, scheme):
        run_validation(handler, False, Request(f'{scheme}://', proxies={scheme: None}))
        run_validation(handler, False, Request(f'{scheme}://'), proxies={scheme: None})

    @pytest.mark.parametrize('proxy_url', ['//example.com', 'example.com', '127.0.0.1', '/a/b/c'])
    @pytest.mark.parametrize('handler,scheme', [
        ('Urllib', 'http'),
        (HTTPSupportedRH, 'http'),
        ('Requests', 'http'),
        ('CurlCFFI', 'http'),
        ('Websockets', 'ws')
    ], indirect=['handler'])
    def test_invalid_proxy_url(self, handler, scheme, proxy_url):
        run_validation(handler, UnsupportedRequest, Request(f'{scheme}://', proxies={scheme: proxy_url}))

    @pytest.mark.parametrize('handler,scheme,fail,handler_kwargs', [
        (handler_tests[0], scheme, fail, handler_kwargs)
        for handler_tests in URL_SCHEME_TESTS
        for scheme, fail, handler_kwargs in handler_tests[1]
    ], indirect=['handler'])
    def test_url_scheme(self, handler, scheme, fail, handler_kwargs):
        run_validation(handler, fail, Request(f'{scheme}://'), **(handler_kwargs or {}))

    @pytest.mark.parametrize('handler,scheme,proxy_key,proxy_scheme,fail', [
        (handler_tests[0], handler_tests[1], proxy_key, proxy_scheme, fail)
        for handler_tests in PROXY_KEY_TESTS
        for proxy_key, proxy_scheme, fail in handler_tests[2]
    ], indirect=['handler'])
    def test_proxy_key(self, handler, scheme, proxy_key, proxy_scheme, fail):
        run_validation(handler, fail, Request(f'{scheme}://', proxies={proxy_key: f'{proxy_scheme}://example.com'}))
        run_validation(handler, fail, Request(f'{scheme}://'), proxies={proxy_key: f'{proxy_scheme}://example.com'})

    @pytest.mark.parametrize('handler,req_scheme,scheme,fail', [
        (handler_tests[0], handler_tests[1], scheme, fail)
        for handler_tests in PROXY_SCHEME_TESTS
        for scheme, fail in handler_tests[2]
    ], indirect=['handler'])
    def test_proxy_scheme(self, handler, req_scheme, scheme, fail):
        run_validation(handler, fail, Request(f'{req_scheme}://', proxies={req_scheme: f'{scheme}://example.com'}))
        run_validation(handler, fail, Request(f'{req_scheme}://'), proxies={req_scheme: f'{scheme}://example.com'})

    @pytest.mark.parametrize('handler,scheme,extensions,fail', [
        (handler_tests[0], handler_tests[1], extensions, fail)
        for handler_tests in EXTENSION_TESTS
        for extensions, fail in handler_tests[2]
    ], indirect=['handler'])
    def test_extension(self, handler, scheme, extensions, fail):
        run_validation(
            handler, fail, Request(f'{scheme}://', extensions=extensions))

    def test_invalid_request_type(self):
        rh = self.ValidationRH(logger=FakeLogger())
        for method in (rh.validate, rh.send):
            with pytest.raises(TypeError, match='Expected an instance of Request'):
                method('not a request')


class FakeResponse(Response):
    def __init__(self, request):
        # XXX: we could make request part of standard response interface
        self.request = request
        super().__init__(fp=io.BytesIO(b''), headers={}, url=request.url)


class FakeRH(RequestHandler):

    def __init__(self, *args, **params):
        self.params = params
        super().__init__(*args, **params)

    def _validate(self, request):
        return

    def _send(self, request: Request):
        if request.url.startswith('ssl://'):
            raise SSLError(request.url[len('ssl://'):])
        return FakeResponse(request)


class FakeRHYDL(FakeYDL):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._request_director = self.build_request_director([FakeRH])


class AllUnsupportedRHYDL(FakeYDL):

    def __init__(self, *args, **kwargs):

        class UnsupportedRH(RequestHandler):
            def _send(self, request: Request):
                pass

            _SUPPORTED_FEATURES = ()
            _SUPPORTED_PROXY_SCHEMES = ()
            _SUPPORTED_URL_SCHEMES = ()

        super().__init__(*args, **kwargs)
        self._request_director = self.build_request_director([UnsupportedRH])


class TestRequestDirector:

    def test_handler_operations(self):
        director = RequestDirector(logger=FakeLogger())
        handler = FakeRH(logger=FakeLogger())
        director.add_handler(handler)
        assert director.handlers.get(FakeRH.RH_KEY) is handler

        # Handler should overwrite
        handler2 = FakeRH(logger=FakeLogger())
        director.add_handler(handler2)
        assert director.handlers.get(FakeRH.RH_KEY) is not handler
        assert director.handlers.get(FakeRH.RH_KEY) is handler2
        assert len(director.handlers) == 1

        class AnotherFakeRH(FakeRH):
            pass
        director.add_handler(AnotherFakeRH(logger=FakeLogger()))
        assert len(director.handlers) == 2
        assert director.handlers.get(AnotherFakeRH.RH_KEY).RH_KEY == AnotherFakeRH.RH_KEY

        director.handlers.pop(FakeRH.RH_KEY, None)
        assert director.handlers.get(FakeRH.RH_KEY) is None
        assert len(director.handlers) == 1

        # RequestErrors should passthrough
        with pytest.raises(SSLError):
            director.send(Request('ssl://something'))

    def test_send(self):
        director = RequestDirector(logger=FakeLogger())
        with pytest.raises(RequestError):
            director.send(Request('any://'))
        director.add_handler(FakeRH(logger=FakeLogger()))
        assert isinstance(director.send(Request('http://')), FakeResponse)

    def test_unsupported_handlers(self):
        class SupportedRH(RequestHandler):
            _SUPPORTED_URL_SCHEMES = ['http']

            def _send(self, request: Request):
                return Response(fp=io.BytesIO(b'supported'), headers={}, url=request.url)

        director = RequestDirector(logger=FakeLogger())
        director.add_handler(SupportedRH(logger=FakeLogger()))
        director.add_handler(FakeRH(logger=FakeLogger()))

        # First should take preference
        assert director.send(Request('http://')).read() == b'supported'
        assert director.send(Request('any://')).read() == b''

        director.handlers.pop(FakeRH.RH_KEY)
        with pytest.raises(NoSupportingHandlers):
            director.send(Request('any://'))

    def test_unexpected_error(self):
        director = RequestDirector(logger=FakeLogger())

        class UnexpectedRH(FakeRH):
            def _send(self, request: Request):
                raise TypeError('something')

        director.add_handler(UnexpectedRH(logger=FakeLogger))
        with pytest.raises(NoSupportingHandlers, match=r'1 unexpected error'):
            director.send(Request('any://'))

        director.handlers.clear()
        assert len(director.handlers) == 0

        # Should not be fatal
        director.add_handler(FakeRH(logger=FakeLogger()))
        director.add_handler(UnexpectedRH(logger=FakeLogger))
        assert director.send(Request('any://'))

    def test_preference(self):
        director = RequestDirector(logger=FakeLogger())
        director.add_handler(FakeRH(logger=FakeLogger()))

        class SomeRH(RequestHandler):
            _SUPPORTED_URL_SCHEMES = ['http']

            def _send(self, request: Request):
                return Response(fp=io.BytesIO(b'supported'), headers={}, url=request.url)

        def some_preference(rh, request):
            return (0 if not isinstance(rh, SomeRH)
                    else 100 if 'prefer' in request.headers
                    else -1)

        director.add_handler(SomeRH(logger=FakeLogger()))
        director.preferences.add(some_preference)

        assert director.send(Request('http://')).read() == b''
        assert director.send(Request('http://', headers={'prefer': '1'})).read() == b'supported'

    def test_close(self, monkeypatch):
        director = RequestDirector(logger=FakeLogger())
        director.add_handler(FakeRH(logger=FakeLogger()))
        called = False

        def mock_close(*args, **kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr(director.handlers[FakeRH.RH_KEY], 'close', mock_close)
        director.close()
        assert called


# XXX: do we want to move this to test_YoutubeDL.py?
class TestYoutubeDLNetworking:

    @staticmethod
    def build_handler(ydl, handler: RequestHandler = FakeRH):
        return ydl.build_request_director([handler]).handlers.get(handler.RH_KEY)

    def test_compat_opener(self):
        with FakeYDL() as ydl:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', category=DeprecationWarning)
                assert isinstance(ydl._opener, urllib.request.OpenerDirector)

    @pytest.mark.parametrize('proxy,expected', [
        ('http://127.0.0.1:8080', {'all': 'http://127.0.0.1:8080'}),
        ('', {'all': '__noproxy__'}),
        (None, {'http': 'http://127.0.0.1:8081', 'https': 'http://127.0.0.1:8081'})  # env, set https
    ])
    def test_proxy(self, proxy, expected, monkeypatch):
        monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:8081')
        with FakeYDL({'proxy': proxy}) as ydl:
            assert ydl.proxies == expected

    def test_compat_request(self):
        with FakeRHYDL() as ydl:
            assert ydl.urlopen('test://')
            urllib_req = urllib.request.Request('http://foo.bar', data=b'test', method='PUT', headers={'X-Test': '1'})
            urllib_req.add_unredirected_header('Cookie', 'bob=bob')
            urllib_req.timeout = 2
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', category=DeprecationWarning)
                req = ydl.urlopen(urllib_req).request
                assert req.url == urllib_req.get_full_url()
                assert req.data == urllib_req.data
                assert req.method == urllib_req.get_method()
                assert 'X-Test' in req.headers
                assert 'Cookie' in req.headers
                assert req.extensions.get('timeout') == 2

            with pytest.raises(AssertionError):
                ydl.urlopen(None)

    def test_extract_basic_auth(self):
        with FakeRHYDL() as ydl:
            res = ydl.urlopen(Request('http://user:pass@foo.bar'))
            assert res.request.headers['Authorization'] == 'Basic dXNlcjpwYXNz'

    def test_sanitize_url(self):
        with FakeRHYDL() as ydl:
            res = ydl.urlopen(Request('httpss://foo.bar'))
            assert res.request.url == 'https://foo.bar'

    def test_file_urls_error(self):
        # use urllib handler
        with FakeYDL() as ydl:
            with pytest.raises(RequestError, match=r'file:// URLs are disabled by default'):
                ydl.urlopen('file://')

    @pytest.mark.parametrize('scheme', (['ws', 'wss']))
    def test_websocket_unavailable_error(self, scheme):
        with AllUnsupportedRHYDL() as ydl:
            with pytest.raises(RequestError, match=r'This request requires WebSocket support'):
                ydl.urlopen(f'{scheme}://')

    def test_legacy_server_connect_error(self):
        with FakeRHYDL() as ydl:
            for error in ('UNSAFE_LEGACY_RENEGOTIATION_DISABLED', 'SSLV3_ALERT_HANDSHAKE_FAILURE'):
                with pytest.raises(RequestError, match=r'Try using --legacy-server-connect'):
                    ydl.urlopen(f'ssl://{error}')

            with pytest.raises(SSLError, match='testerror'):
                ydl.urlopen('ssl://testerror')

    def test_unsupported_impersonate_target(self):
        class FakeImpersonationRHYDL(FakeYDL):
            def __init__(self, *args, **kwargs):
                class HTTPRH(RequestHandler):
                    def _send(self, request: Request):
                        pass
                    _SUPPORTED_URL_SCHEMES = ('http',)
                    _SUPPORTED_PROXY_SCHEMES = None

                super().__init__(*args, **kwargs)
                self._request_director = self.build_request_director([HTTPRH])

        with FakeImpersonationRHYDL() as ydl:
            with pytest.raises(
                RequestError,
                match=r'Impersonate target "test" is not available'
            ):
                ydl.urlopen(Request('http://', extensions={'impersonate': ImpersonateTarget('test', None, None, None)}))

    def test_unsupported_impersonate_extension(self):
        class FakeHTTPRHYDL(FakeYDL):
            def __init__(self, *args, **kwargs):
                class IRH(ImpersonateRequestHandler):
                    def _send(self, request: Request):
                        pass

                    _SUPPORTED_URL_SCHEMES = ('http',)
                    _SUPPORTED_IMPERSONATE_TARGET_MAP = {ImpersonateTarget('abc',): 'test'}
                    _SUPPORTED_PROXY_SCHEMES = None

                super().__init__(*args, **kwargs)
                self._request_director = self.build_request_director([IRH])

        with FakeHTTPRHYDL() as ydl:
            with pytest.raises(
                RequestError,
                match=r'Impersonate target "test" is not available'
            ):
                ydl.urlopen(Request('http://', extensions={'impersonate': ImpersonateTarget('test', None, None, None)}))

    def test_raise_impersonate_error(self):
        with pytest.raises(
            YoutubeDLError,
            match=r'Impersonate target "test" is not available'
        ):
            FakeYDL({'impersonate': ImpersonateTarget('test', None, None, None)})

    def test_pass_impersonate_param(self, monkeypatch):

        class IRH(ImpersonateRequestHandler):
            def _send(self, request: Request):
                pass

            _SUPPORTED_URL_SCHEMES = ('http',)
            _SUPPORTED_IMPERSONATE_TARGET_MAP = {ImpersonateTarget('abc'): 'test'}

        # Bypass the check on initialize
        brh = FakeYDL.build_request_director
        monkeypatch.setattr(FakeYDL, 'build_request_director', lambda cls, handlers, preferences=None: brh(cls, handlers=[IRH]))

        with FakeYDL({
            'impersonate': ImpersonateTarget('abc', None, None, None)
        }) as ydl:
            rh = self.build_handler(ydl, IRH)
            assert rh.impersonate == ImpersonateTarget('abc', None, None, None)

    def test_get_impersonate_targets(self):
        handlers = []
        for target_client in ('abc', 'xyz', 'asd'):
            class TestRH(ImpersonateRequestHandler):
                def _send(self, request: Request):
                    pass
                _SUPPORTED_URL_SCHEMES = ('http',)
                _SUPPORTED_IMPERSONATE_TARGET_MAP = {ImpersonateTarget(target_client,): 'test'}
                RH_KEY = target_client
                RH_NAME = target_client
            handlers.append(TestRH)

        with FakeYDL() as ydl:
            ydl._request_director = ydl.build_request_director(handlers)
            assert set(ydl._get_available_impersonate_targets()) == {
                (ImpersonateTarget('xyz'), 'xyz'),
                (ImpersonateTarget('abc'), 'abc'),
                (ImpersonateTarget('asd'), 'asd')
            }
            assert ydl._impersonate_target_available(ImpersonateTarget('abc'))
            assert ydl._impersonate_target_available(ImpersonateTarget())
            assert not ydl._impersonate_target_available(ImpersonateTarget('zxy'))

    @pytest.mark.parametrize('proxy_key,proxy_url,expected', [
        ('http', '__noproxy__', None),
        ('no', '127.0.0.1,foo.bar', '127.0.0.1,foo.bar'),
        ('https', 'example.com', 'http://example.com'),
        ('https', '//example.com', 'http://example.com'),
        ('https', 'socks5://example.com', 'socks5h://example.com'),
        ('http', 'socks://example.com', 'socks4://example.com'),
        ('http', 'socks4://example.com', 'socks4://example.com'),
        ('unrelated', '/bad/proxy', '/bad/proxy'),  # clean_proxies should ignore bad proxies
    ])
    def test_clean_proxy(self, proxy_key, proxy_url, expected, monkeypatch):
        # proxies should be cleaned in urlopen()
        with FakeRHYDL() as ydl:
            req = ydl.urlopen(Request('test://', proxies={proxy_key: proxy_url})).request
            assert req.proxies[proxy_key] == expected

        # and should also be cleaned when building the handler
        monkeypatch.setenv(f'{proxy_key.upper()}_PROXY', proxy_url)
        with FakeYDL() as ydl:
            rh = self.build_handler(ydl)
            assert rh.proxies[proxy_key] == expected

    def test_clean_proxy_header(self):
        with FakeRHYDL() as ydl:
            req = ydl.urlopen(Request('test://', headers={'ytdl-request-proxy': '//foo.bar'})).request
            assert 'ytdl-request-proxy' not in req.headers
            assert req.proxies == {'all': 'http://foo.bar'}

        with FakeYDL({'http_headers': {'ytdl-request-proxy': '//foo.bar'}}) as ydl:
            rh = self.build_handler(ydl)
            assert 'ytdl-request-proxy' not in rh.headers
            assert rh.proxies == {'all': 'http://foo.bar'}

    def test_clean_header(self):
        with FakeRHYDL() as ydl:
            res = ydl.urlopen(Request('test://', headers={'Youtubedl-no-compression': True}))
            assert 'Youtubedl-no-compression' not in res.request.headers
            assert res.request.headers.get('Accept-Encoding') == 'identity'

        with FakeYDL({'http_headers': {'Youtubedl-no-compression': True}}) as ydl:
            rh = self.build_handler(ydl)
            assert 'Youtubedl-no-compression' not in rh.headers
            assert rh.headers.get('Accept-Encoding') == 'identity'

        with FakeYDL({'http_headers': {'Ytdl-socks-proxy': 'socks://localhost:1080'}}) as ydl:
            rh = self.build_handler(ydl)
            assert 'Ytdl-socks-proxy' not in rh.headers

    def test_build_handler_params(self):
        with FakeYDL({
            'http_headers': {'test': 'testtest'},
            'socket_timeout': 2,
            'proxy': 'http://127.0.0.1:8080',
            'source_address': '127.0.0.45',
            'debug_printtraffic': True,
            'compat_opts': ['no-certifi'],
            'nocheckcertificate': True,
            'legacyserverconnect': True,
        }) as ydl:
            rh = self.build_handler(ydl)
            assert rh.headers.get('test') == 'testtest'
            assert 'Accept' in rh.headers  # ensure std_headers are still there
            assert rh.timeout == 2
            assert rh.proxies.get('all') == 'http://127.0.0.1:8080'
            assert rh.source_address == '127.0.0.45'
            assert rh.verbose is True
            assert rh.prefer_system_certs is True
            assert rh.verify is False
            assert rh.legacy_ssl_support is True

    @pytest.mark.parametrize('ydl_params', [
        {'client_certificate': 'fakecert.crt'},
        {'client_certificate': 'fakecert.crt', 'client_certificate_key': 'fakekey.key'},
        {'client_certificate': 'fakecert.crt', 'client_certificate_key': 'fakekey.key', 'client_certificate_password': 'foobar'},
        {'client_certificate_key': 'fakekey.key', 'client_certificate_password': 'foobar'},
    ])
    def test_client_certificate(self, ydl_params):
        with FakeYDL(ydl_params) as ydl:
            rh = self.build_handler(ydl)
            assert rh._client_cert == ydl_params  # XXX: Too bound to implementation

    def test_urllib_file_urls(self):
        with FakeYDL({'enable_file_urls': False}) as ydl:
            rh = self.build_handler(ydl, UrllibRH)
            assert rh.enable_file_urls is False

        with FakeYDL({'enable_file_urls': True}) as ydl:
            rh = self.build_handler(ydl, UrllibRH)
            assert rh.enable_file_urls is True

    def test_compat_opt_prefer_urllib(self):
        # This assumes urllib only has a preference when this compat opt is given
        with FakeYDL({'compat_opts': ['prefer-legacy-http-handler']}) as ydl:
            director = ydl.build_request_director([UrllibRH])
            assert len(director.preferences) == 1
            assert director.preferences.pop()(UrllibRH, None)


class TestRequest:

    def test_query(self):
        req = Request('http://example.com?q=something', query={'v': 'xyz'})
        assert req.url == 'http://example.com?q=something&v=xyz'

        req.update(query={'v': '123'})
        assert req.url == 'http://example.com?q=something&v=123'
        req.update(url='http://example.com', query={'v': 'xyz'})
        assert req.url == 'http://example.com?v=xyz'

    def test_method(self):
        req = Request('http://example.com')
        assert req.method == 'GET'
        req.data = b'test'
        assert req.method == 'POST'
        req.data = None
        assert req.method == 'GET'
        req.data = b'test2'
        req.method = 'PUT'
        assert req.method == 'PUT'
        req.data = None
        assert req.method == 'PUT'
        with pytest.raises(TypeError):
            req.method = 1

    def test_request_helpers(self):
        assert HEADRequest('http://example.com').method == 'HEAD'
        assert PUTRequest('http://example.com').method == 'PUT'

    def test_headers(self):
        req = Request('http://example.com', headers={'tesT': 'test'})
        assert req.headers == HTTPHeaderDict({'test': 'test'})
        req.update(headers={'teSt2': 'test2'})
        assert req.headers == HTTPHeaderDict({'test': 'test', 'test2': 'test2'})

        req.headers = new_headers = HTTPHeaderDict({'test': 'test'})
        assert req.headers == HTTPHeaderDict({'test': 'test'})
        assert req.headers is new_headers

        # test converts dict to case insensitive dict
        req.headers = new_headers = {'test2': 'test2'}
        assert isinstance(req.headers, HTTPHeaderDict)
        assert req.headers is not new_headers

        with pytest.raises(TypeError):
            req.headers = None

    def test_data_type(self):
        req = Request('http://example.com')
        assert req.data is None
        # test bytes is allowed
        req.data = b'test'
        assert req.data == b'test'
        # test iterable of bytes is allowed
        i = [b'test', b'test2']
        req.data = i
        assert req.data == i

        # test file-like object is allowed
        f = io.BytesIO(b'test')
        req.data = f
        assert req.data == f

        # common mistake: test str not allowed
        with pytest.raises(TypeError):
            req.data = 'test'
        assert req.data != 'test'

        # common mistake: test dict is not allowed
        with pytest.raises(TypeError):
            req.data = {'test': 'test'}
        assert req.data != {'test': 'test'}

    def test_content_length_header(self):
        req = Request('http://example.com', headers={'Content-Length': '0'}, data=b'')
        assert req.headers.get('Content-Length') == '0'

        req.data = b'test'
        assert 'Content-Length' not in req.headers

        req = Request('http://example.com', headers={'Content-Length': '10'})
        assert 'Content-Length' not in req.headers

    def test_content_type_header(self):
        req = Request('http://example.com', headers={'Content-Type': 'test'}, data=b'test')
        assert req.headers.get('Content-Type') == 'test'
        req.data = b'test2'
        assert req.headers.get('Content-Type') == 'test'
        req.data = None
        assert 'Content-Type' not in req.headers
        req.data = b'test3'
        assert req.headers.get('Content-Type') == 'application/x-www-form-urlencoded'

    def test_update_req(self):
        req = Request('http://example.com')
        assert req.data is None
        assert req.method == 'GET'
        assert 'Content-Type' not in req.headers
        # Test that zero-byte payloads will be sent
        req.update(data=b'')
        assert req.data == b''
        assert req.method == 'POST'
        assert req.headers.get('Content-Type') == 'application/x-www-form-urlencoded'

    def test_proxies(self):
        req = Request(url='http://example.com', proxies={'http': 'http://127.0.0.1:8080'})
        assert req.proxies == {'http': 'http://127.0.0.1:8080'}

    def test_extensions(self):
        req = Request(url='http://example.com', extensions={'timeout': 2})
        assert req.extensions == {'timeout': 2}

    def test_copy(self):
        req = Request(
            url='http://example.com',
            extensions={'cookiejar': CookieJar()},
            headers={'Accept-Encoding': 'br'},
            proxies={'http': 'http://127.0.0.1'},
            data=[b'123']
        )
        req_copy = req.copy()
        assert req_copy is not req
        assert req_copy.url == req.url
        assert req_copy.headers == req.headers
        assert req_copy.headers is not req.headers
        assert req_copy.proxies == req.proxies
        assert req_copy.proxies is not req.proxies

        # Data is not able to be copied
        assert req_copy.data == req.data
        assert req_copy.data is req.data

        # Shallow copy extensions
        assert req_copy.extensions is not req.extensions
        assert req_copy.extensions['cookiejar'] == req.extensions['cookiejar']

        # Subclasses are copied by default
        class AnotherRequest(Request):
            pass

        req = AnotherRequest(url='http://127.0.0.1')
        assert isinstance(req.copy(), AnotherRequest)

    def test_url(self):
        req = Request(url='https://фtest.example.com/ some spaceв?ä=c',)
        assert req.url == 'https://xn--test-z6d.example.com/%20some%20space%D0%B2?%C3%A4=c'

        assert Request(url='//example.com').url == 'http://example.com'

        with pytest.raises(TypeError):
            Request(url='https://').url = None


class TestResponse:

    @pytest.mark.parametrize('reason,status,expected', [
        ('custom', 200, 'custom'),
        (None, 404, 'Not Found'),  # fallback status
        ('', 403, 'Forbidden'),
        (None, 999, None)
    ])
    def test_reason(self, reason, status, expected):
        res = Response(io.BytesIO(b''), url='test://', headers={}, status=status, reason=reason)
        assert res.reason == expected

    def test_headers(self):
        headers = Message()
        headers.add_header('Test', 'test')
        headers.add_header('Test', 'test2')
        headers.add_header('content-encoding', 'br')
        res = Response(io.BytesIO(b''), headers=headers, url='test://')
        assert res.headers.get_all('test') == ['test', 'test2']
        assert 'Content-Encoding' in res.headers

    def test_get_header(self):
        headers = Message()
        headers.add_header('Set-Cookie', 'cookie1')
        headers.add_header('Set-cookie', 'cookie2')
        headers.add_header('Test', 'test')
        headers.add_header('Test', 'test2')
        res = Response(io.BytesIO(b''), headers=headers, url='test://')
        assert res.get_header('test') == 'test, test2'
        assert res.get_header('set-Cookie') == 'cookie1'
        assert res.get_header('notexist', 'default') == 'default'

    def test_compat(self):
        res = Response(io.BytesIO(b''), url='test://', status=404, headers={'test': 'test'})
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=DeprecationWarning)
            assert res.code == res.getcode() == res.status
            assert res.geturl() == res.url
            assert res.info() is res.headers
            assert res.getheader('test') == res.get_header('test')


class TestImpersonateTarget:
    @pytest.mark.parametrize('target_str,expected', [
        ('abc', ImpersonateTarget('abc', None, None, None)),
        ('abc-120_esr', ImpersonateTarget('abc', '120_esr', None, None)),
        ('abc-120:xyz', ImpersonateTarget('abc', '120', 'xyz', None)),
        ('abc-120:xyz-5.6', ImpersonateTarget('abc', '120', 'xyz', '5.6')),
        ('abc:xyz', ImpersonateTarget('abc', None, 'xyz', None)),
        ('abc:', ImpersonateTarget('abc', None, None, None)),
        ('abc-120:', ImpersonateTarget('abc', '120', None, None)),
        (':xyz', ImpersonateTarget(None, None, 'xyz', None)),
        (':xyz-6.5', ImpersonateTarget(None, None, 'xyz', '6.5')),
        (':', ImpersonateTarget(None, None, None, None)),
        ('', ImpersonateTarget(None, None, None, None)),
    ])
    def test_target_from_str(self, target_str, expected):
        assert ImpersonateTarget.from_str(target_str) == expected

    @pytest.mark.parametrize('target_str', [
        '-120', ':-12.0', '-12:-12', '-:-',
        '::', 'a-c-d:', 'a-c-d:e-f-g', 'a:b:'
    ])
    def test_target_from_invalid_str(self, target_str):
        with pytest.raises(ValueError):
            ImpersonateTarget.from_str(target_str)

    @pytest.mark.parametrize('target,expected', [
        (ImpersonateTarget('abc', None, None, None), 'abc'),
        (ImpersonateTarget('abc', '120', None, None), 'abc-120'),
        (ImpersonateTarget('abc', '120', 'xyz', None), 'abc-120:xyz'),
        (ImpersonateTarget('abc', '120', 'xyz', '5'), 'abc-120:xyz-5'),
        (ImpersonateTarget('abc', None, 'xyz', None), 'abc:xyz'),
        (ImpersonateTarget('abc', '120', None, None), 'abc-120'),
        (ImpersonateTarget('abc', '120', 'xyz', None), 'abc-120:xyz'),
        (ImpersonateTarget('abc', None, 'xyz'), 'abc:xyz'),
        (ImpersonateTarget(None, None, 'xyz', '6.5'), ':xyz-6.5'),
        (ImpersonateTarget('abc', ), 'abc'),
        (ImpersonateTarget(None, None, None, None), ''),
    ])
    def test_str(self, target, expected):
        assert str(target) == expected

    @pytest.mark.parametrize('args', [
        ('abc', None, None, '5'),
        ('abc', '120', None, '5'),
        (None, '120', None, None),
        (None, '120', None, '5'),
        (None, None, None, '5'),
        (None, '120', 'xyz', '5'),
    ])
    def test_invalid_impersonate_target(self, args):
        with pytest.raises(ValueError):
            ImpersonateTarget(*args)

    @pytest.mark.parametrize('target1,target2,is_in,is_eq', [
        (ImpersonateTarget('abc', None, None, None), ImpersonateTarget('abc', None, None, None), True, True),
        (ImpersonateTarget('abc', None, None, None), ImpersonateTarget('abc', '120', None, None), True, False),
        (ImpersonateTarget('abc', None, 'xyz', 'test'), ImpersonateTarget('abc', '120', 'xyz', None), True, False),
        (ImpersonateTarget('abc', '121', 'xyz', 'test'), ImpersonateTarget('abc', '120', 'xyz', 'test'), False, False),
        (ImpersonateTarget('abc'), ImpersonateTarget('abc', '120', 'xyz', 'test'), True, False),
        (ImpersonateTarget('abc', '120', 'xyz', 'test'), ImpersonateTarget('abc'), True, False),
        (ImpersonateTarget(), ImpersonateTarget('abc', '120', 'xyz'), True, False),
        (ImpersonateTarget(), ImpersonateTarget(), True, True),
    ])
    def test_impersonate_target_in(self, target1, target2, is_in, is_eq):
        assert (target1 in target2) is is_in
        assert (target1 == target2) is is_eq
