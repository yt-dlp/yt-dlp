#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gzip
import http.cookiejar
import functools
import gzip
import http.client
import http.server
import io
import pathlib
import io
import ssl
import tempfile
import threading
import urllib.error
import urllib.request
import zlib
import urllib.error

from http.cookiejar import Cookie

from test.helper import FakeYDL, http_server_port
from yt_dlp import YoutubeDL
from yt_dlp.dependencies import brotli
from yt_dlp.utils import sanitized_Request, urlencode_postdata

from .helper import FakeYDL
from yt_dlp.networking import Request, UrllibRH, list_request_handler_classes, RequestHandler, Response
from yt_dlp.utils import urlencode_postdata
from yt_dlp.networking.exceptions import HTTPError, IncompleteRead, SSLError, UnsupportedRequest, RequestError

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

ALL_REQUEST_HANDLERS = list_request_handler_classes()


class FakeLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

class HTTPTestRequestHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1' # required for persistent connections

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


class FakeLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class TestHTTP(unittest.TestCase):
    def setUp(self):
        # HTTP server
        self.http_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.http_port = http_server_port(self.http_httpd)
        self.http_server_thread = threading.Thread(target=self.http_httpd.serve_forever)
        # FIXME: we should probably stop the http server thread after each test
        # See: https://github.com/yt-dlp/yt-dlp/pull/7094#discussion_r1199746041
        self.http_server_thread.daemon = True
        self.http_server_thread.start()

        # HTTPS server
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.https_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.load_cert_chain(certfn, None)
        self.https_httpd.socket = sslctx.wrap_socket(self.https_httpd.socket, server_side=True)
        self.https_port = http_server_port(self.https_httpd)
        self.https_server_thread = threading.Thread(target=self.https_httpd.serve_forever)
        self.https_server_thread.daemon = True
        self.https_server_thread.start()

    def test_nocheckcertificate(self):
        with FakeYDL({'logger': FakeLogger()}) as ydl:
            with self.assertRaises(urllib.error.URLError):
                ydl.urlopen(sanitized_Request(f'https://127.0.0.1:{self.https_port}/headers'))

        with FakeYDL({'logger': FakeLogger(), 'nocheckcertificate': True}) as ydl:
            r = ydl.urlopen(sanitized_Request(f'https://127.0.0.1:{self.https_port}/headers'))
            self.assertEqual(r.status, 200)
            r.close()

    def test_percent_encode(self):
        with FakeYDL() as ydl:
            # Unicode characters should be encoded with uppercase percent-encoding
            res = ydl.urlopen(sanitized_Request(f'http://127.0.0.1:{self.http_port}/中文.html'))
            self.assertEqual(res.status, 200)
            res.close()
            # don't normalize existing percent encodings
            res = ydl.urlopen(sanitized_Request(f'http://127.0.0.1:{self.http_port}/%c7%9f'))
            self.assertEqual(res.status, 200)
            res.close()

    def test_unicode_path_redirection(self):
        with FakeYDL() as ydl:
            r = ydl.urlopen(sanitized_Request(f'http://127.0.0.1:{self.http_port}/302-non-ascii-redirect'))
            self.assertEqual(r.url, f'http://127.0.0.1:{self.http_port}/%E4%B8%AD%E6%96%87.html')
            r.close()

    def test_redirect(self):
        with FakeYDL() as ydl:
            def do_req(redirect_status, method):
                data = b'testdata' if method in ('POST', 'PUT') else None
                res = ydl.urlopen(sanitized_Request(
                    f'http://127.0.0.1:{self.http_port}/redirect_{redirect_status}', method=method, data=data))
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
            for m in ('POST', 'PUT'):
                self.assertEqual(do_req(307, m), ('testdata', m))
                self.assertEqual(do_req(308, m), ('testdata', m))

            self.assertEqual(do_req(307, 'HEAD'), ('', 'HEAD'))
            self.assertEqual(do_req(308, 'HEAD'), ('', 'HEAD'))

            # These should not redirect and instead raise an HTTPError
            for code in (300, 304, 305, 306):
                with self.assertRaises(urllib.error.HTTPError):
                    do_req(code, 'GET')

    def test_content_type(self):
        # https://github.com/yt-dlp/yt-dlp/commit/379a4f161d4ad3e40932dcf5aca6e6fb9715ab28
        with FakeYDL({'nocheckcertificate': True}) as ydl:
            # method should be auto-detected as POST
            r = sanitized_Request(f'https://localhost:{self.https_port}/headers', data=urlencode_postdata({'test': 'test'}))

            headers = ydl.urlopen(r).read().decode('utf-8')
            self.assertIn('Content-Type: application/x-www-form-urlencoded', headers)

            # test http
            r = sanitized_Request(f'http://localhost:{self.http_port}/headers', data=urlencode_postdata({'test': 'test'}))
            headers = ydl.urlopen(r).read().decode('utf-8')
            self.assertIn('Content-Type: application/x-www-form-urlencoded', headers)

    def test_cookiejar(self):
        with FakeYDL() as ydl:
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(
                0, 'test', 'ytdlp', None, False, '127.0.0.1', True,
                False, '/headers', True, False, None, False, None, None, {}))
            data = ydl.urlopen(sanitized_Request(f'http://127.0.0.1:{self.http_port}/headers')).read()
            self.assertIn(b'Cookie: test=ytdlp', data)

    def test_no_compression_compat_header(self):
        with FakeYDL() as ydl:
            data = ydl.urlopen(
                sanitized_Request(
                    f'http://127.0.0.1:{self.http_port}/headers',
                    headers={'Youtubedl-no-compression': True})).read()
            self.assertIn(b'Accept-Encoding: identity', data)
            self.assertNotIn(b'youtubedl-no-compression', data.lower())

    def test_gzip_trailing_garbage(self):
        # https://github.com/ytdl-org/youtube-dl/commit/aa3e950764337ef9800c936f4de89b31c00dfcf5
        # https://github.com/ytdl-org/youtube-dl/commit/6f2ec15cee79d35dba065677cad9da7491ec6e6f
        with FakeYDL() as ydl:
            data = ydl.urlopen(sanitized_Request(f'http://localhost:{self.http_port}/trailing_garbage')).read().decode('utf-8')
            self.assertEqual(data, '<html><video src="/vid.mp4" /></html>')

    @unittest.skipUnless(brotli, 'brotli support is not installed')
    def test_brotli(self):
        with FakeYDL() as ydl:
            res = ydl.urlopen(
                sanitized_Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'br'}))
            self.assertEqual(res.headers.get('Content-Encoding'), 'br')
            self.assertEqual(res.read(), b'<html><video src="/vid.mp4" /></html>')

    def test_deflate(self):
        with FakeYDL() as ydl:
            res = ydl.urlopen(
                sanitized_Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'deflate'}))
            self.assertEqual(res.headers.get('Content-Encoding'), 'deflate')
            self.assertEqual(res.read(), b'<html><video src="/vid.mp4" /></html>')

    def test_gzip(self):
        with FakeYDL() as ydl:
            res = ydl.urlopen(
                sanitized_Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'gzip'}))
            self.assertEqual(res.headers.get('Content-Encoding'), 'gzip')
            self.assertEqual(res.read(), b'<html><video src="/vid.mp4" /></html>')

    def test_multiple_encodings(self):
        # https://www.rfc-editor.org/rfc/rfc9110.html#section-8.4
        with FakeYDL() as ydl:
            for pair in ('gzip,deflate', 'deflate, gzip', 'gzip, gzip', 'deflate, deflate'):
                res = ydl.urlopen(
                    sanitized_Request(
                        f'http://127.0.0.1:{self.http_port}/content-encoding',
                        headers={'ytdl-encoding': pair}))
                self.assertEqual(res.headers.get('Content-Encoding'), pair)
                self.assertEqual(res.read(), b'<html><video src="/vid.mp4" /></html>')

    def test_unsupported_encoding(self):
        # it should return the raw content
        with FakeYDL() as ydl:
            res = ydl.urlopen(
                sanitized_Request(
                    f'http://127.0.0.1:{self.http_port}/content-encoding',
                    headers={'ytdl-encoding': 'unsupported'}))
            self.assertEqual(res.headers.get('Content-Encoding'), 'unsupported')
            self.assertEqual(res.read(), b'raw')


class TestClientCert(unittest.TestCase):
    def setUp(self):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.certdir = os.path.join(TEST_DIR, 'testdata', 'certificate')
        cacertfn = os.path.join(self.certdir, 'ca.crt')
        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), HTTPTestRequestHandler)
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
            rh.handle(Request(f'https://127.0.0.1:{self.port}/video.html')).read().decode('utf-8')

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
    def test_file_urls(self, make_rh):
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.write(b'foobar')
        tf.close()
        req = Request(pathlib.Path(tf.name).as_uri())
        with make_rh() as rh:
            self.assertRaises(UnsupportedRequest, rh.handle, req)
            self.assertRaisesRegex(
                urllib.error.URLError, 'urlopen error unknown url type: file', rh.ydl._opener.open, req.url)
        with make_rh({'enable_file_urls': True}) as rh:
            try:
                res = rh.handle(req)
                self.assertEqual(res.read(), b'foobar')
                res.close()
            except UnsupportedRequest:
                self.fail('UnsupportedRequest raised')

            res = rh.ydl._opener.open(req.url)
            self.assertEqual(res.read(), b'foobar')
            res.close()
        os.unlink(tf.name)


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

    def test_handler_preference(self):
        class MockHandlerRH(RequestHandler):
            def handle(self, request: Request):
                return Response(io.BytesIO(self.rh_key().encode('utf-8')), url=request.url, headers={})

        class MockHandler2RH(MockHandlerRH):
            pass

        class MockHandlerFallbackRH(RequestHandler):
            def prepare_request(self, request: Request):
                raise UnsupportedRequest('no support')

        with FakeYDL() as ydl:
            rd = ydl.build_request_director([MockHandlerFallbackRH, MockHandler2RH, MockHandlerRH, UrllibRH, ])

            req = Request(url='http://127.0.0.1:%d/headers' % self.http_port)
            self.assertNotIn(b'MockHandler', rd.send(req).read())

            req.preferred_handlers.insert(0, MockHandlerRH.rh_key())
            self.assertEqual(rd.send(req).read(), b'MockHandler')
            req.preferred_handlers.insert(0, MockHandler2RH.rh_key())
            self.assertEqual(rd.send(req).read(), b'MockHandler2')
            req.preferred_handlers.insert(0, MockHandlerFallbackRH.rh_key())
            self.assertEqual(rd.send(req).read(), b'MockHandler2')
            req.preferred_handlers.insert(0, 'I do not exist')
            self.assertEqual(rd.send(req).read(), b'MockHandler2')
            req.preferred_handlers.insert(0, 'Urllib')
            self.assertNotIn(b'MockHandler', rd.send(req).read())


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


class TestFileURL(unittest.TestCase):
    # See https://github.com/ytdl-org/youtube-dl/issues/8227
    def test_file_urls(self):
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.write(b'foobar')
        tf.close()
        url = pathlib.Path(tf.name).as_uri()
        with FakeYDL() as ydl:
            self.assertRaisesRegex(
                urllib.error.URLError, 'file:// URLs are explicitly disabled in yt-dlp for security reasons', ydl.urlopen, url)
        with FakeYDL({'enable_file_urls': True}) as ydl:
            res = ydl.urlopen(url)
            self.assertEqual(res.read(), b'foobar')
            res.close()
        os.unlink(tf.name)


if __name__ == '__main__':
    unittest.main()
