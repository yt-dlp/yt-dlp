#!/usr/bin/env python3

# Allow direct execution
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from yt_dlp.networking import get_request_handler, RequestHandler, Response, RequestDirector
from yt_dlp.networking.utils import std_headers
import gzip
import http.cookiejar
import functools
import http.client
import http.server
import io
import pathlib
import ssl
import tempfile
import threading
import urllib.error
import urllib.request
import zlib
import urllib.error

from test.helper import http_server_port
from yt_dlp import YoutubeDL
from yt_dlp.dependencies import brotli

from .helper import FakeYDL
from yt_dlp.networking import Request, UrllibRH, list_request_handler_classes
from yt_dlp.networking.exceptions import HTTPError, IncompleteRead, SSLError, UnsupportedRequest, RequestError, \
    TransportError, NoSupportingHandlers
from yt_dlp.utils import urlencode_postdata, CaseInsensitiveDict, YoutubeDLError

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def _build_proxy_handler(name):
    class HTTPTestRequestHandler(http.server.BaseHTTPRequestHandler):
        proxy_name = name

        def log_message(self, format, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('{self.proxy_name}: {self.path}'.format(self=self).encode('utf-8'))
    return HTTPTestRequestHandler


class FakeLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

    def to_debugtraffic(self, msg):
        pass

    def report_error(self, *args, **kwargs):
        pass


class HTTPTestRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'  # required for persistent connections

    def log_message(self, format, *args):
        pass

    def _headers(self):
        payload = str(self.headers).encode('utf-8')
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

    def do_POST(self):
        data = self._read_data()
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
        data = self._read_data()
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
            self.send_header('Content-Length', str(len(payload)))  # required for persistent connections
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
        elif self.path.startswith('/redirect_'):
            self._redirect()
        elif self.path.startswith('/method'):
            self._method('GET')
        elif self.path.startswith('/headers'):
            self._headers()
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
            payload = str(self.client_address[0]).encode('utf-8')
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


def validate_and_send(rh, req):
    rh.validate(req)
    return rh.send(req)


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


@pytest.fixture
def handler(request):
    rh_key = request.param
    try:
        handler = get_request_handler(rh_key)
    except KeyError:
        handler = None
    if handler is None:
        pytest.skip(f'{rh_key} request handler is not available')

    return functools.partial(handler, logger=FakeLogger)


class TestHTTPRequestHandler(TestRequestHandlerBase):
    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_verify_cert(self, handler):
        with handler() as rh:
            with pytest.raises(SSLError):
                validate_and_send(rh, Request(f'https://127.0.0.1:{self.https_port}/headers'))

        with handler(verify=False) as rh:
            r = validate_and_send(rh, Request(f'https://127.0.0.1:{self.https_port}/headers'))
            assert r.status == 200
            r.close()

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
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

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_unicode_path_redirection(self, handler):
        with handler() as rh:
            r = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/302-non-ascii-redirect'))
            assert r.url == f'http://127.0.0.1:{self.http_port}/%E4%B8%AD%E6%96%87.html'
            r.close()

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_raise_http_error(self, handler):
        with handler() as rh:
            for bad_status in (400, 500, 599, 302):
                with pytest.raises(HTTPError):
                    validate_and_send(rh, Request('http://127.0.0.1:%d/gen_%d' % (self.http_port, bad_status)))

            # Should not raise an error
            validate_and_send(rh, Request('http://127.0.0.1:%d/gen_200' % self.http_port)).close()

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_response_url(self, handler):
        with handler() as rh:
            # Response url should be that of the last url in redirect chain
            res = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/redirect_301'))
            assert res.url == f'http://127.0.0.1:{self.http_port}/method'
            res.close()
            res2 = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/gen_200'))
            assert res2.url == f'http://127.0.0.1:{self.http_port}/gen_200'
            res2.close()

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_redirect(self, handler):
        with handler() as rh:
            def do_req(redirect_status, method):
                data = b'testdata' if method in ('POST', 'PUT') else None
                res = validate_and_send(rh,
                    Request(f'http://127.0.0.1:{self.http_port}/redirect_{redirect_status}', method=method,
                            data=data))
                return res.read().decode('utf-8'), res.headers.get('method', '')

            # A 303 must either use GET or HEAD for subsequent request
            assert do_req(303, 'POST') == ('', 'GET')
            assert do_req(303, 'HEAD') == ('', 'HEAD')

            assert do_req(303, 'PUT') == ('', 'GET')

            # 301 and 302 turn POST only into a GET
            assert do_req(301, 'POST') == ('', 'GET')
            assert do_req(301, 'HEAD') == ('', 'HEAD')
            assert do_req(302, 'POST') == ('', 'GET')
            assert do_req(302, 'HEAD') == ('', 'HEAD')

            assert do_req(301, 'PUT') == ('testdata', 'PUT')
            assert do_req(302, 'PUT') == ('testdata', 'PUT')

            # 307 and 308 should not change method
            for m in ('POST', 'PUT'):
                assert do_req(307, m) == ('testdata', m)
                assert do_req(308, m) == ('testdata', m)

            assert do_req(307, 'HEAD') == ('', 'HEAD')
            assert do_req(308, 'HEAD') == ('', 'HEAD')

            # These should not redirect and instead raise an HTTPError
            for code in (300, 304, 305, 306):
                with pytest.raises(urllib.error.HTTPError):
                    do_req(code, 'GET')

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_incompleteread(self, handler):
        with handler(timeout=2) as rh:  # TODO: add timeout test
            with pytest.raises(IncompleteRead):
                validate_and_send(rh, Request('http://127.0.0.1:%d/incompleteread' % self.http_port)).read()

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_cookies(self, handler):
        cookiejar = http.cookiejar.CookieJar()
        cookiejar.set_cookie(http.cookiejar.Cookie(
            0, 'test', 'ytdlp', None, False, '127.0.0.1', True,
            False, '/headers', True, False, None, False, None, None, {}))

        with handler(cookiejar=cookiejar) as rh:
            data = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/headers')).read()
            assert b'Cookie: test=ytdlp' in data

        # Per request
        with handler() as rh:
            data = validate_and_send(rh,
                Request(f'http://127.0.0.1:{self.http_port}/headers', extensions={'cookiejar': cookiejar})).read()
            assert b'Cookie: test=ytdlp' in data

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_headers(self, handler):

        with handler(headers=CaseInsensitiveDict({'test1': 'test', 'test2': 'test2'})) as rh:
            # Global Headers
            data = validate_and_send(rh, Request(f'http://127.0.0.1:{self.http_port}/headers')).read()
            assert b'Test1: test' in data

            # Per request headers, merged with global
            data = validate_and_send(rh, Request(
                f'http://127.0.0.1:{self.http_port}/headers', headers={'test2': 'changed', 'test3': 'test3'})).read()
            assert b'Test1: test' in data
            assert b'Test2: changed' in data
            assert b'Test2: test2' not in data
            assert b'Test3: test3' in data

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_timeout(self, handler):
        with handler() as rh:
            # Default timeout is 20 seconds, so this should go through
            validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/timeout_3'))

        with handler(timeout=0.5) as rh:
            with pytest.raises(TransportError):
                validate_and_send(
                    rh, Request(f'http://127.0.0.1:{self.http_port}/timeout_1'))

            # Per request timeout, should override handler timeout
            validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/timeout_1', extensions={'timeout': 4}))

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_source_address(self, handler):
        source_address = f'127.0.0.{random.randint(5, 255)}'
        with handler(source_address=source_address) as rh:
            data = validate_and_send(
                rh, Request(f'http://127.0.0.1:{self.http_port}/source_address')).read().decode('utf-8')
            assert source_address == data

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_gzip_trailing_garbage(self, handler):
        with handler() as rh:
            data = validate_and_send(rh, Request(f'http://localhost:{self.http_port}/trailing_garbage')).read().decode('utf-8')
            assert data == '<html><video src="/vid.mp4" /></html>'

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    @pytest.mark.skipif(not brotli, reason='brotli support is not installed')
    def test_brotli(self, handler):
        with handler() as rh:
            res = validate_and_send(rh,
                Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'br'}))
            assert res.headers.get('Content-Encoding') == 'br'
            assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_deflate(self, handler):
        with handler() as rh:
            res = validate_and_send(rh,
                Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'deflate'}))
            assert res.headers.get('Content-Encoding') == 'deflate'
            assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_gzip(self, handler):
        with handler() as rh:
            res = validate_and_send(rh,
                Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'gzip'}))
            assert res.headers.get('Content-Encoding') == 'gzip'
            assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_multiple_encodings(self, handler):
        with handler() as rh:
            for pair in ('gzip,deflate', 'deflate, gzip', 'gzip, gzip', 'deflate, deflate'):
                res = validate_and_send(rh,
                    Request(
                        f'http://127.0.0.1:{self.http_port}/content-encoding',
                        headers={'ytdl-encoding': pair}))
                assert res.headers.get('Content-Encoding') == pair
                assert res.read() == b'<html><video src="/vid.mp4" /></html>'

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_unsupported_encoding(self, handler):
        with handler() as rh:
            res = validate_and_send(rh,
                Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'unsupported'}))
            assert res.headers.get('Content-Encoding') == 'unsupported'
            assert res.read() == b'raw'


class TestHTTPProxy(TestRequestHandlerBase):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        # HTTP Proxy server
        cls.proxy = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('normal'))
        cls.proxy_port = http_server_port(cls.proxy)
        cls.proxy_thread = threading.Thread(target=cls.proxy.serve_forever)
        cls.proxy_thread.daemon = True
        cls.proxy_thread.start()

        # Geo proxy server
        cls.geo_proxy = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('geo'))
        cls.geo_port = http_server_port(cls.geo_proxy)
        cls.geo_proxy_thread = threading.Thread(target=cls.geo_proxy.serve_forever)
        cls.geo_proxy_thread.daemon = True
        cls.geo_proxy_thread.start()

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_http_proxy(self, handler):
        http_proxy = f'http://127.0.0.1:{self.proxy_port}'
        geo_proxy = f'http://127.0.0.1:{self.geo_port}'

        # Test global http proxy
        # Test per request http proxy
        # Test per request http proxy disables proxy
        url = 'http://foo.com/bar'

        # Global HTTP proxy
        with handler(proxies={'http': http_proxy}) as rh:
            res = validate_and_send(rh, Request(url)).read().decode('utf-8')
            assert res == f'normal: {url}'

            # Per request proxy overrides global
            res = validate_and_send(rh, Request(url, proxies={'http': geo_proxy})).read().decode('utf-8')
            assert res == f'geo: {url}'

            # and setting to None disables all proxies for that request
            real_url = f'http://127.0.0.1:{self.http_port}/headers'
            res = validate_and_send(rh,
                Request(real_url, proxies={'http': None})).read().decode('utf-8')
            assert res != f'normal: {real_url}'
            assert 'Accept' in res

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_noproxy(self, handler):
        with handler(proxies={'proxy': f'http://127.0.0.1:{self.proxy_port}'}) as rh:
            # NO_PROXY
            for no_proxy in (f'127.0.0.1:{self.http_port}', '127.0.0.1', 'localhost'):
                nop_response = validate_and_send(rh,
                    Request(f'http://127.0.0.1:{self.http_port}/headers', proxies={'no': no_proxy})).read().decode(
                    'utf-8')
                assert 'Accept' in nop_response

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_allproxy(self, handler):
        url = 'http://foo.com/bar'
        with handler() as rh:
            response = validate_and_send(rh, Request(url, proxies={'all': f'http://127.0.0.1:{self.proxy_port}'})).read().decode(
                'utf-8')
            assert response == f'normal: {url}'

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_http_proxy_with_idn(self, handler):
        with handler(proxies={
            'http': f'http://127.0.0.1:{self.proxy_port}',
        }) as rh:
            url = 'http://中文.tw/'
            response = rh.send(Request(url)).read().decode('utf-8')
            # b'xn--fiq228c' is '中文'.encode('idna')
            assert response == 'normal: http://xn--fiq228c.tw/'


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
            validate_and_send(rh, Request(f'https://127.0.0.1:{self.port}/video.html')).read().decode('utf-8')

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_certificate_combined_nopass(self, handler):
        self._run_test(handler, client_cert=(os.path.join(self.certdir, 'clientwithkey.crt'), None, None))

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_certificate_nocombined_nopass(self, handler):
        self._run_test(handler, client_cert=(os.path.join(self.certdir, 'client.crt'), os.path.join(self.certdir, 'client.key'), None))

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_certificate_combined_pass(self, handler):
        self._run_test(handler, client_cert=(os.path.join(self.certdir, 'clientwithencryptedkey.crt'), None, 'foobar'))

    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
    def test_certificate_nocombined_pass(self, handler):
        self._run_test(handler, client_cert=(os.path.join(self.certdir, 'client.crt'), os.path.join(self.certdir, 'clientencrypted.key'),'foobar'))


class TestUrllibRequestHandler(TestRequestHandlerBase):
    @pytest.mark.parametrize('handler', ['Urllib'], indirect=True)
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


def run_validation(handler, fail, req, **handler_kwargs):
    with handler(**handler_kwargs) as rh:
        if fail:
            with pytest.raises(UnsupportedRequest):
                rh.validate(req)
        else:
            rh.validate(req)


# TODO: may want to create a dummy request handler to test the core behaviour
# Then real handler specific code can me more simpler and specific to it
@pytest.mark.parametrize('handler', ['Urllib'], indirect=['handler'])
class TestUrllibRHValidation:
    @pytest.mark.parametrize('scheme,fail,handler_kwargs', [
        ('http', False, {}),
        ('https', False, {}),
        ('data', False, {}),
        ('ftp', False, {}),
        ('file', True, {}),
        ('file', False, {'enable_file_urls': True}),
    ])
    def test_url_scheme(self, handler, scheme, fail, handler_kwargs):
        run_validation(handler, fail, Request(f'{scheme}://'), **(handler_kwargs or {}))

    def test_no_proxy(self, handler):
        run_validation(handler, False, Request(f'http://', proxies={'no': '127.0.0.1,github.com'}))
        run_validation(handler, False, Request(f'http://'), proxies={'no': '127.0.0.1,github.com'})

    def test_all_proxy(self, handler):
        run_validation(handler, False, Request(f'http://', proxies={'all': 'http://example.com'}))
        run_validation(handler, False, Request(f'http://'), proxies={'all': 'http://example.com'})

    def test_unrelated_proxy(self, handler):
        run_validation(handler, False, Request(f'http://', proxies={'unrelated': 'http://example.com'}))
        run_validation(handler, False, Request(f'http://'), proxies={'unrelated': 'http://example.com'})

    @pytest.mark.parametrize('scheme', ['http', 'socks', 'socks5', 'socks4a', 'socks4'])
    def test_proxy_scheme(self, handler, scheme):
        run_validation(handler, False, Request(f'http://', proxies={'http': f'{scheme}://example.com'}))
        run_validation(handler, False, Request(f'http://'), proxies={'http': f'{scheme}://example.com'})

    @pytest.mark.parametrize('scheme', ['https', 'test'])
    def test_unsupported_proxy_scheme(self, handler, scheme):
        run_validation(handler, True, Request(f'http://', proxies={'http': f'{scheme}://example.com'}))
        run_validation(handler, True, Request(f'http://'), proxies={'http': f'{scheme}://example.com'})

    @pytest.mark.parametrize('proxy_url', ['//example.com', 'example.com', '127.0.0.1'])
    def test_missing_proxy_scheme(self, handler, proxy_url):
        run_validation(handler, True, Request(f'http://', proxies={'http': f'example.com'}))

    def test_cookiejar_extension(self, handler):
        run_validation(handler, True, Request(f'http://', extensions={'cookiejar': 'notacookiejar'}))

    def test_timeout_extension(self, handler):
        run_validation(handler, True, Request(f'http://', extensions={'timeout': 'notavalidtimeout'}))


class FakeResponse(Response):
    def __init__(self, request):
        # XXX: we could make request part of standard response interface
        self.request = request
        super().__init__(raw=io.BytesIO(b''), headers={}, url=request.url)


class FakeRH(RequestHandler):

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


class TestRequestDirector:

    def test_handler_operations(self):
        director = RequestDirector(FakeLogger())
        handler = FakeRH(FakeLogger())
        director.add_handler(handler)
        assert director.get_handler(FakeRH.rh_key()) is handler

        # Handler should overwrite
        handler2 = FakeRH(FakeLogger())
        director.add_handler(handler2)
        assert director.get_handler(FakeRH.rh_key()) is not handler
        assert director.get_handler(FakeRH.rh_key()) is handler2
        assert len(director.get_handlers()) == 1

        class AnotherFakeRH(FakeRH):
            pass
        director.add_handler(AnotherFakeRH(FakeLogger()))
        assert len(director.get_handlers()) == 2
        assert director.get_handler(AnotherFakeRH.rh_key()).rh_key() == AnotherFakeRH.rh_key()

        director.remove_handler(FakeRH.rh_key())
        assert director.get_handler(FakeRH.rh_key()) is None
        assert len(director.get_handlers()) == 1

        # RequestErrors should passthrough
        with pytest.raises(SSLError):
            director.send(Request('ssl://something'))

    def test_send(self):
        director = RequestDirector(FakeLogger())
        with pytest.raises(RequestError):
            director.send(Request('any://'))
        director.add_handler(FakeRH(FakeLogger()))
        assert isinstance(director.send(Request('http://')), FakeResponse)

    def test_unsupported_handlers(self):
        director = RequestDirector(FakeLogger())
        director.add_handler(FakeRH(FakeLogger()))

        class SupportedRH(RequestHandler):
            _SUPPORTED_URL_SCHEMES = ['http']

            def _send(self, request: Request):
                return Response(raw=io.BytesIO(b'supported'), headers={}, url=request.url)

        # This handler should by default take preference over FakeRH
        director.add_handler(SupportedRH(FakeLogger()))
        assert director.send(Request('http://')).read() == b'supported'
        assert director.send(Request('any://')).read() == b''

        director.remove_handler(FakeRH.rh_key())
        with pytest.raises(NoSupportingHandlers):
            director.send(Request('any://'))

    def test_unexpected_error(self):
        director = RequestDirector(FakeLogger())


        class UnexpectedRH(FakeRH):
            def _send(self, request: Request):
                raise TypeError('something')

        director.add_handler(UnexpectedRH(FakeLogger))
        with pytest.raises(NoSupportingHandlers, match=r'1 unexpected error'):
            director.send(Request('any://'))

        director.remove_handlers()
        assert len(director.get_handlers()) == 0

        # Should not be fatal
        director.add_handler(FakeRH(FakeLogger()))
        director.add_handler(UnexpectedRH(FakeLogger))
        assert director.send(Request('any://'))


class TestYoutubeDLHTTP:

    def test_compat_opener(self):
        with FakeYDL() as ydl:
            assert isinstance(ydl._opener, urllib.request.OpenerDirector)

    @pytest.mark.parametrize('proxy,expected', [
        ('http://127.0.0.1:8080', {'all': 'http://127.0.0.1:8080'}),
        ('', {'all': '__noproxy__'}),
        (None, {'http': 'http://127.0.0.1:8081', 'https': 'http://127.0.0.1:8081'})  # env, set https
    ])
    def test_proxy(self, proxy, expected):
        old_http_proxy = os.environ.get('HTTP_PROXY')
        try:
            os.environ['HTTP_PROXY'] = 'http://127.0.0.1:8081'  # ensure that provided proxies override env
            with FakeYDL({'proxy': proxy}) as ydl:
                assert ydl.proxies == expected
        finally:
            if old_http_proxy:
                os.environ['HTTP_PROXY'] = old_http_proxy

    def test_compat_request(self):
        with FakeRHYDL() as ydl:
            assert ydl.urlopen('test://')
            urllib_req = urllib.request.Request('http://foo.bar', data=b'test', method='PUT', headers={'X-Test': '1'})
            urllib_req.add_unredirected_header('Cookie', 'bob=bob')
            urllib_req.timeout = 2
            req = ydl.urlopen(urllib_req).request
            assert req.url == urllib_req.get_full_url()
            assert req.data == urllib_req.data
            assert req.method == urllib_req.get_method()
            assert 'X-Test' in req.headers
            assert 'Cookie' in req.headers
            assert req.extensions.get('timeout') == 2

            with pytest.raises(AssertionError):
                ydl.urlopen(None)

    def test_compat_compression(self):
        with FakeRHYDL() as ydl:
            res = ydl.urlopen(Request('test://', headers={'Youtubedl-no-compression': True}))
            assert 'Youtubedl-no-compression' not in res.request.headers
            assert res.request.headers.get('Accept-Encoding') == 'identity'

    def test_extract_basic_auth(self):
        with FakeRHYDL() as ydl:
            res = ydl.urlopen(Request('http://user:pass@foo.bar'))
            assert res.request.headers['Authorization'] == 'Basic dXNlcjpwYXNz'

    def test_file_urls_error(self):
        # use urllib handler
        with FakeYDL() as ydl:
            with pytest.raises(YoutubeDLError, match=r'file:// URLs are disabled by default'):
                ydl.urlopen('file://')

    def test_legacy_server_connect_error(self):
        with FakeRHYDL() as ydl:
            for error in ('UNSAFE_LEGACY_RENEGOTIATION_DISABLED', 'SSLV3_ALERT_HANDSHAKE_FAILURE'):
                with pytest.raises(YoutubeDLError, match=r'Try using --legacy-server-connect'):
                    ydl.urlopen(f'ssl://{error}')

            with pytest.raises(SSLError, match='testerror'):
                ydl.urlopen(f'ssl://testerror')

    def test_clean_proxy(self):
        with FakeRHYDL() as ydl:
            get_req = lambda x: ydl.urlopen(x).request
            req = get_req(Request('test://', headers={'ytdl-request-proxy': '//foo.bar'}))
            assert 'ytdl-request-proxy' not in req.headers
            assert req.proxies['all'] == 'http://foo.bar'

            req = get_req(Request('test://', proxies={'http': '__noproxy__', 'no': '127.0.0.1,foo.bar', 'https': 'example.com'}))
            assert req.proxies['http'] == None
            assert req.proxies['no'] == '127.0.0.1,foo.bar'
            assert req.proxies['https'] == 'http://example.com'


class TestYDLRequestDirectorBuilder:

    @staticmethod
    def build_handler(ydl, handler=FakeRH):
        return ydl.build_request_director([handler]).get_handler(rh_key=handler.rh_key())

    def test_default_params(self):
        with FakeYDL() as ydl:
            rh = self.build_handler(ydl)
            assert rh.headers.items() == std_headers.items()
            assert rh.timeout == 20.0
            assert rh.source_address is None
            assert rh.verbose is False
            assert rh.prefer_system_certs is False
            assert rh.verify is True
            assert rh.legacy_ssl_support is False
            assert rh.client_cert is None
            assert rh.cookiejar is ydl.cookiejar

    def test_params(self):
        with FakeYDL({
            'http_headers': {'test': 'testtest'},
            'socket_timeout': 2,
            'proxy': 'http://127.0.0.1:8080',
            'source_address': '127.0.0.45',
            'debug_printtraffic': True,
            'compat_opts': ['no-certifi'],
            'nocheckcertificate': True,
            'legacy_server_connect': True,
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

    @pytest.mark.parametrize('ydl_params,expected', [
        ({'client_certificate': 'fakecert.crt'}, ('fakecert.crt', None, None)),
        ({'client_certificate': 'fakecert.crt', 'client_certificate_key': 'fakekey.key'}, ('fakecert.crt', 'fakekey.key', None)),
        ({'client_certificate': 'fakecert.crt', 'client_certificate_key': 'fakekey.key',
          'client_certificate_password': 'foobar'}, ('fakecert.crt', 'fakekey.key', 'foobar')),
        ({'client_certificate_key': 'fakekey.key', 'client_certificate_password': 'foobar'}, None),
    ])
    def test_client_certificate(self, ydl_params, expected):
        with FakeYDL(ydl_params) as ydl:
            rh = self.build_handler(ydl)
            assert rh.client_cert == expected

    def test_urllib_file_urls(self):
        with FakeYDL({'enable_file_urls': False}) as ydl:
            rh = self.build_handler(ydl, UrllibRH)
            assert rh.enable_file_urls is False

        with FakeYDL({'enable_file_urls': True}) as ydl:
            rh = self.build_handler(ydl, UrllibRH)
            assert rh.enable_file_urls is True
