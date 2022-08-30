#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import functools
import gzip
import http.client
import http.server
import io
import ssl
import threading
import urllib.request
import urllib.error

from http.cookiejar import Cookie

from test.helper import FakeYDL, http_server_port
from yt_dlp import YoutubeDL
from yt_dlp.networking import Request, UrllibRH, REQUEST_HANDLERS
from yt_dlp.utils import urlencode_postdata
from yt_dlp.networking.exceptions import HTTPError, IncompleteRead, SSLError, UnsupportedRequest, RequestError

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

ALL_REQUEST_HANDLERS = REQUEST_HANDLERS


class FakeLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class HTTPServerRequestHandler(http.server.BaseHTTPRequestHandler):
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
        elif self.path.startswith('/gen_'):
            payload = b'<html></html>'
            self.send_response(int(self.path[len('/gen_'):]))
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
        elif self.path.startswith('/incompleteread'):
            payload = b'<html></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', '234234')
            self.end_headers()
            self.wfile.write(payload)
            self.finish()
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
            compressed = buf.getvalue()
            self.send_header('Content-Length', str(len(compressed) + len(b'trailing garbage')))
            self.end_headers()
            self.wfile.write(compressed + b'trailing garbage')
        elif self.path == '/302-non-ascii-redirect':
            new_url = 'http://127.0.0.1:%d/中文.html' % http_server_port(self.server)
            self.send_response(301)
            self.send_header('Location', new_url)
            self.send_header('Content-Length', '0')
            self.end_headers()
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

# TODO: what to do with request handlers that do not support everything
# TODO: is there a better way


def with_make_rh(handlers=None, ignore_handlers=None):
    # XXX: it might be better/easier to use pytest
    handlers = [h for h in (handlers or ALL_REQUEST_HANDLERS) if h not in (ignore_handlers or [])]

    def make_ydl(handler, params=None, fake=True):
        ydl = (FakeYDL if fake else YoutubeDL)(params)
        ydl._request_director = ydl.build_request_director([handler])
        return ydl

    @contextmanager
    def make_rh(handler, ydl_params=None, ydl_fake=True):
        ydl = make_ydl(handler, ydl_params, ydl_fake)
        try:
            yield ydl._request_director.get_handlers(handler)[0]
        finally:
            ydl.close()

    def inner_func(test):
        @functools.wraps(test)
        def wrapper(self, *args, **kwargs):
            for handler in handlers:
                if handler is None:  # TODO: should we show handler being skipped? how would we get name?
                    continue
                with self.subTest(handler=handler.NAME):
                    try:
                        test(self, functools.partial(make_rh, handler), *args, **kwargs)
                    except UnsupportedRequest as e:
                        self.skipTest(f'Skipping, unsupported test for {handler.NAME} handler: {e}')
        return wrapper
    return inner_func


class RequestHandlerTestCase(unittest.TestCase):
    def setUp(self):
        # HTTP server
        self.http_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPServerRequestHandler)
        self.http_port = http_server_port(self.http_httpd)
        self.http_server_thread = threading.Thread(target=self.http_httpd.serve_forever)
        self.http_server_thread.daemon = True
        self.http_server_thread.start()

        # HTTPS server
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.https_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPServerRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.load_cert_chain(certfn, None)
        self.https_httpd.socket = sslctx.wrap_socket(self.https_httpd.socket, server_side=True)
        self.https_port = http_server_port(self.https_httpd)
        self.https_server_thread = threading.Thread(target=self.https_httpd.serve_forever)
        self.https_server_thread.daemon = True
        self.https_server_thread.start()

        # HTTP Proxy server
        self.proxy = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('normal'))
        self.proxy_port = http_server_port(self.proxy)
        self.proxy_thread = threading.Thread(target=self.proxy.serve_forever)
        self.proxy_thread.daemon = True
        self.proxy_thread.start()

        # Geo proxy server
        self.geo_proxy = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('geo'))
        self.geo_port = http_server_port(self.geo_proxy)
        self.geo_proxy_thread = threading.Thread(target=self.geo_proxy.serve_forever)
        self.geo_proxy_thread.daemon = True
        self.geo_proxy_thread.start()


class TestRequestHandler(RequestHandlerTestCase):

    @with_make_rh()
    def test_raise(self, make_rh):
        with make_rh() as rh:
            for func in (rh.handle, rh.prepare_request, functools.partial(rh.can_handle, fatal=True)):
                try:
                    func(Request('bad123://'))
                except RequestError as e:
                    self.assertIs(e.handler, rh)

            with self.assertRaises(TypeError):
                rh.handle(None)

    @with_make_rh()
    def test_nocheckcertificate(self, make_rh):
        with make_rh({'logger': FakeLogger()}) as rh:
            with self.assertRaises(SSLError):
                rh.handle(Request('https://127.0.0.1:%d/headers' % self.https_port))

        with make_rh({'logger': FakeLogger(), 'nocheckcertificate': True}) as rh:
            r = rh.handle(Request('https://127.0.0.1:%d/headers' % self.https_port))
            self.assertEqual(r.status, 200)

    @with_make_rh()
    def test_percent_encode(self, make_rh):
        with make_rh() as rh:
            # Unicode characters should be encoded with uppercase percent-encoding
            res = rh.handle(Request(f'http://127.0.0.1:{self.http_port}/中文.html'))
            self.assertEqual(res.status, 200)

            # don't normalize existing percent encodings
            res = rh.handle(Request(f'http://127.0.0.1:{self.http_port}/%c7%9f'))
            self.assertEqual(res.status, 200)

    @with_make_rh()
    def test_unicode_path_redirection(self, make_rh):
        with make_rh() as rh:
            r = rh.handle(Request('http://127.0.0.1:%d/302-non-ascii-redirect' % self.http_port))
            self.assertEqual(r.url, f'http://127.0.0.1:{self.http_port}/%E4%B8%AD%E6%96%87.html')

    @with_make_rh()
    def test_raise_http_error(self, make_rh):
        with make_rh() as rh:
            for bad_status in (400, 500, 599, 302):
                with self.assertRaises(HTTPError):
                    rh.handle(Request('http://127.0.0.1:%d/gen_%d' % (self.http_port, bad_status)))

            # Should not raise an error
            rh.handle(Request('http://127.0.0.1:%d/gen_200' % self.http_port))

    @with_make_rh()
    def test_redirect_loop(self, make_rh):
        with make_rh() as rh:
            with self.assertRaisesRegex(HTTPError, r'HTTP Error 301: Moved Permanently \(redirect loop detected\)'):
                rh.handle(Request('http://127.0.0.1:%d/redirect_loop' % self.http_port))

    @with_make_rh()
    def test_get_url(self, make_rh):
        with make_rh() as rh:
            res = rh.handle(Request('http://127.0.0.1:%d/redirect_301' % self.http_port))
            self.assertEqual(res.url, 'http://127.0.0.1:%d/method' % self.http_port)
            res2 = rh.handle(Request('http://127.0.0.1:%d/gen_200' % self.http_port))
            self.assertEqual(res2.url, 'http://127.0.0.1:%d/gen_200' % self.http_port)

    @with_make_rh()
    def test_redirect(self, make_rh):
        with make_rh() as rh:
            def do_req(redirect_status, method):
                data = b'testdata' if method in ('POST', 'PUT') else None
                res = rh.handle(
                    Request(f'http://127.0.0.1:%d/redirect_{redirect_status}' % self.http_port, method=method, data=data))
                return res.read().decode('utf-8'), res.headers.get('method', '')

            # A 303 must either use GET or HEAD for subsequent request
            self.assertEqual(do_req(303, 'POST'), ('', 'GET'))
            self.assertEqual(do_req(303, 'HEAD'), ('', 'HEAD'))

            self.assertEqual(do_req(303, 'PUT'), ('', 'GET'))

            # 301 and 302 turn POST only into a GET
            self.assertEqual(do_req(301, 'POST'), ('', 'GET'))
            self.assertEqual(do_req(301, 'HEAD'), ('', 'HEAD'))
            self.assertEqual(do_req(302, 'POST'), ('', 'GET'))
            self.assertEqual(do_req(302, 'HEAD'), ('', 'HEAD'))

            self.assertEqual(do_req(301, 'PUT'), ('testdata', 'PUT'))
            self.assertEqual(do_req(302, 'PUT'), ('testdata', 'PUT'))

            # 307 and 308 should not change method
            self.assertEqual(do_req(307, 'POST'), ('testdata', 'POST'))
            self.assertEqual(do_req(308, 'POST'), ('testdata', 'POST'))

            # These should not redirect and instead raise an HTTPError
            for code in (300, 304, 305, 306):
                with self.assertRaises(HTTPError):
                    do_req(code, 'GET')

    @with_make_rh()
    def test_no_redirects(self, make_rh):
        with make_rh() as rh:
            res = rh.handle(Request('http://localhost:%d/redirect_302' % self.http_port, allow_redirects=False))
            self.assertEqual(res.status, 302)

    @with_make_rh()
    def test_content_type(self, make_rh):
        with make_rh({'nocheckcertificate': True}) as rh:
            # method should be auto-detected as POST
            r = Request('https://localhost:%d/headers' % self.https_port, data=urlencode_postdata({'test': 'test'}))

            headers = rh.handle(r).read().decode('utf-8')
            self.assertIn('Content-Type: application/x-www-form-urlencoded', headers)

            # test http
            r.update(url='http://localhost:%d/headers' % self.http_port)
            headers = rh.handle(r).read().decode('utf-8')
            self.assertIn('Content-Type: application/x-www-form-urlencoded', headers)

    @with_make_rh()
    def test_incompleteread(self, make_rh):
        with make_rh({'socket_timeout': 2}) as rh:
            with self.assertRaises(IncompleteRead):
                rh.handle(Request('http://127.0.0.1:%d/incompleteread' % self.http_port)).read()

    @with_make_rh()
    def test_cookiejar(self, make_rh):
        with make_rh() as rh:
            rh.ydl.cookiejar.set_cookie(
                Cookie(
                    0, 'test', 'ytdlp', None, False, '127.0.0.1', True,
                    False, '/headers', True, False, None, False, None, None, {}))
            data = rh.handle(Request('http://127.0.0.1:%d/headers' % self.http_port)).read()
            self.assertIn(b'Cookie: test=ytdlp', data)

    @with_make_rh()
    def test_no_compression(self, make_rh):
        # TODO: add compression as features
        with make_rh() as rh:
            url = 'http://127.0.0.1:%d/headers' % self.http_port
            for request in (Request(url, compression=False), Request(url, headers={'Youtubedl-no-compression': '1'})):
                data = rh.handle(request).read()
                if b'Accept-Encoding' in data:
                    self.assertIn(b'Accept-Encoding: identity', data)

    @with_make_rh()
    def test_gzip_trailing_garbage(self, make_rh):
        # TODO: add gzip compression as feature maybe
        # https://github.com/ytdl-org/youtube-dl/commit/aa3e950764337ef9800c936f4de89b31c00dfcf5
        # https://github.com/ytdl-org/youtube-dl/commit/6f2ec15cee79d35dba065677cad9da7491ec6e6f
        with make_rh() as rh:
            data = rh.handle(Request('http://localhost:%d/trailing_garbage' % self.http_port)).read().decode('utf-8')
            self.assertEqual(data, '<html><video src="/vid.mp4" /></html>')


class TestClientCert(unittest.TestCase):
    def setUp(self):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.certdir = os.path.join(TEST_DIR, 'testdata', 'certificate')
        cacertfn = os.path.join(self.certdir, 'ca.crt')
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), HTTPServerRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.verify_mode = ssl.CERT_REQUIRED
        sslctx.load_verify_locations(cafile=cacertfn)
        sslctx.load_cert_chain(certfn, None)
        self.httpd.socket = sslctx.wrap_socket(self.httpd.socket, server_side=True)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    @with_make_rh()
    def _run_test(self, make_rh, **params):
        with make_rh({
            'logger': FakeLogger(),
            # Disable client-side validation of unacceptable self-signed testcert.pem
            # The test is of a check on the server side, so unaffected
            'nocheckcertificate': True,
            **params,
        }, ydl_fake=False) as rh:
            rh.handle(Request('https://127.0.0.1:%d/video.html' % self.port)).read().decode('utf-8')

    def test_certificate_combined_nopass(self):
        self._run_test(client_certificate=os.path.join(self.certdir, 'clientwithkey.crt'))

    def test_certificate_nocombined_nopass(self):
        self._run_test(client_certificate=os.path.join(self.certdir, 'client.crt'),
                       client_certificate_key=os.path.join(self.certdir, 'client.key'))

    def test_certificate_combined_pass(self):
        self._run_test(client_certificate=os.path.join(self.certdir, 'clientwithencryptedkey.crt'),
                       client_certificate_password='foobar')

    def test_certificate_nocombined_pass(self):
        self._run_test(client_certificate=os.path.join(self.certdir, 'client.crt'),
                       client_certificate_key=os.path.join(self.certdir, 'clientencrypted.key'),
                       client_certificate_password='foobar')


class TestUrllibRequestHandler(RequestHandlerTestCase):
    @with_make_rh([UrllibRH])
    def test_ydl_compat_opener(self, make_rh):
        with make_rh() as rh:
            res = rh.ydl._opener.open('http://127.0.0.1:%d/gen_200' % self.http_port)
            self.assertIsInstance(res, http.client.HTTPResponse)

    @with_make_rh([UrllibRH])
    def test_file_protocol(self, make_rh):
        with tempfile.NamedTemporaryFile() as t:
            t.write(b'foobar')
            t.flush()
            req = Request(f'file://{t.name}')
            with make_rh() as rh:
                self.assertRaises(UnsupportedRequest, rh.handle, req)
                self.assertRaisesRegex(
                    urllib.error.URLError, 'urlopen error unknown url type: file', rh.ydl._opener.open, req.url)
            with make_rh({'enable_file_protocol': True}) as rh:
                try:
                    res = rh.handle(req)
                    self.assertEqual(res.read(), b'foobar')
                except UnsupportedRequest:
                    self.fail('UnsupportedRequest raised')

                res = rh.ydl._opener.open(req.url)
                self.assertEqual(res.read(), b'foobar')


class TestRequestDirector(RequestHandlerTestCase):
    def test_request_types(self):
        with FakeYDL() as ydl:
            rd = ydl._request_director

            url = 'http://127.0.0.1:%d/headers' % self.http_port
            test_header = {'X-ydl-test': '1'}
            # by url
            self.assertTrue(rd.send(url).read())

            # urllib Request compat and ydl Request
            for request in (urllib.request.Request(url, headers=test_header), Request(url, headers=test_header)):
                data = rd.send(request).read()
                self.assertIn(b'X-Ydl-Test: 1', data)

            with self.assertRaises(AssertionError):
                rd.send(None)


class TestHTTPProxy(RequestHandlerTestCase):
    @with_make_rh()
    def test_http_proxy(self, make_rh):
        geo_proxy = f'127.0.0.1:{self.geo_port}'
        geo_proxy2 = f'localhost:{self.geo_port}'  # tests no scheme handling

        url = 'http://foo.com/bar'
        with make_rh({
            'proxy': f'//127.0.0.1:{self.proxy_port}',
            'geo_verification_proxy': geo_proxy,
        }) as rh:
            response = rh.handle(Request(url)).read().decode('utf-8')
            self.assertEqual(response, f'normal: {url}')

            # Test Ytdl-request-proxy header
            req = Request(url, headers={'Ytdl-request-proxy': geo_proxy2})
            response1 = rh.handle(req).read().decode('utf-8')
            self.assertEqual(response1, f'geo: {url}')

            # Test proxies dict in request
            response2 = rh.handle(Request(url, proxies={'http': geo_proxy})).read().decode('utf-8')
            self.assertEqual(response2, f'geo: {url}')

            # test that __noproxy__ disables all proxies for that request
            real_url = 'http://127.0.0.1:%d/headers' % self.http_port
            response3 = rh.handle(
                Request(real_url, headers={'Ytdl-request-proxy': '__noproxy__'})).read().decode('utf-8')
            self.assertNotEqual(response3, f'normal: {real_url}')
            self.assertNotIn('Ytdl-request-proxy', response3)
            self.assertIn('Accept', response3)

            # test unrelated proxy is ignored (would cause all handlers to be unsupported otherwise)
            response4 = rh.handle(
                Request('http://localhost:%d/headers' % self.http_port,
                        proxies={'unrelated': 'unrelated://example.com'})).read().decode('utf-8')
            self.assertIn('Accept', response4)

    @with_make_rh()
    def test_no_proxy(self, make_rh):
        with make_rh({'proxy': f'http://127.0.0.1:{self.proxy_port}'}) as rh:
            # NO_PROXY
            for no_proxy in (f'127.0.0.1:{self.http_port}', '127.0.0.1', 'localhost'):
                nop_response = rh.handle(Request(f'http://127.0.0.1:{self.http_port}/headers', proxies={'no': no_proxy})).read().decode('utf-8')
                self.assertIn('Accept', nop_response)

    @with_make_rh()
    def test_all_proxy(self, make_rh):
        # test all proxy
        url = 'http://foo.com/bar'
        with make_rh() as rh:
            response = rh.handle(Request(url, proxies={'all': f'http://127.0.0.1:{self.proxy_port}'})).read().decode('utf-8')
            self.assertEqual(response, f'normal: {url}')

    @with_make_rh()
    def test_http_proxy_with_idn(self, make_rh):
        with make_rh({
            'proxy': f'127.0.0.1:{self.proxy_port}',
        }) as rh:
            url = 'http://中文.tw/'
            response = rh.handle(Request(url)).read().decode('utf-8')
            # b'xn--fiq228c' is '中文'.encode('idna')
            self.assertEqual(response, 'normal: http://xn--fiq228c.tw/')


if __name__ == '__main__':
    unittest.main()
