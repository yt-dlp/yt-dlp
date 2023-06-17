#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from yt_dlp.networking import get_request_handler, RequestHandler
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
    TransportError
from yt_dlp.utils import urlencode_postdata

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

class TestRequestHandler:
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

    @pytest.fixture
    def handler(self, request):
        rh_key = request.param
        try:
            handler = get_request_handler(rh_key)
        except KeyError:
            handler = None
        if handler is None:
            pytest.skip(f'{rh_key} request handler is not available')

        return functools.partial(handler, logger=FakeLogger)

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

    # TODO: split out into separate urllib rh tests
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

        os.unlink(tf.name)

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
