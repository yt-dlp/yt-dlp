import functools
import gzip
import io
import os
import sys
import unittest
import urllib.request
from http.cookiejar import Cookie

from yt_dlp.networking import UrllibRH, UnsupportedRH, Request, HEADRequest
from yt_dlp.utils import HTTPError, SSLError, TransportError, IncompleteRead

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import http_server_port, FakeYDL
from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_http_server
import ssl
import threading
import http.server
import http.client

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

HTTP_TEST_BACKEND_HANDLERS = [UrllibRH]


class FakeLogger(object):
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

    def _redirect(self):
        self.send_response(int(self.path[len('/redirect_'):]))
        self.send_header('Location', '/gen_204')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _404(self):
        payload = b'<html>404 NOT FOUND</html>'
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_HEAD(self):
        if self.path.startswith('/redirect_'):
            self._redirect()
        else:
            self._404()

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
        elif self.path.startswith('/incompleteread'):
            payload = b'<html></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', '234234')
            self.end_headers()
            self.wfile.write(payload)
            self.finish()
        elif self.path.startswith('/headers'):
            payload = str(self.headers).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/trailing_garbage':
            payload = b'<html><video src="/vid.mp4" /></html>'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Encoding', 'gzip')
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode='wb') as f:
                f.write(payload)
            compressed = buf.getvalue()
            self.send_header('Content-Length', str(len(compressed)+len(b'trailing garbage')))
            self.end_headers()
            self.wfile.write(compressed + b'trailing garbage')
        elif self.path == '/302-non-ascii-redirect':
            new_url = 'http://127.0.0.1:%d/中文.html' % http_server_port(self.server)
            self.send_response(301)
            self.send_header('Location', new_url)
            self.send_header('Content-Length', '0')
            self.end_headers()
        else:
            self._404()

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

        self._headers_buffer.append(f'{keyword}: {value}\r\n'.encode('utf-8'))


def _build_proxy_handler(name):
    class HTTPTestRequestHandler(compat_http_server.BaseHTTPRequestHandler):
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


class RequestHandlerTestBase:
    handler = None

    def make_ydl(self, params=None, fake=True):
        ydl = (FakeYDL if fake else YoutubeDL)(params)

        ydl.http = ydl.build_http([UnsupportedRH, self.handler])
        return ydl


class RequestHandlerCommonTestsBase(RequestHandlerTestBase):
    def setUp(self):
        # HTTP server
        self.http_httpd = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.http_port = http_server_port(self.http_httpd)
        self.http_server_thread = threading.Thread(target=self.http_httpd.serve_forever)
        self.http_server_thread.daemon = True
        self.http_server_thread.start()

        # HTTPS server
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.https_httpd = compat_http_server.ThreadingHTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
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

    def test_nocheckcertificate(self):
        with self.make_ydl({'logger': FakeLogger()}) as ydl:
            self.assertRaises(
                SSLError,
                ydl.urlopen, 'https://127.0.0.1:%d/video.html' % self.https_port)
        with self.make_ydl({'logger': FakeLogger(), 'nocheckcertificate': True}, fake=False) as ydl:
            r = ydl.extract_info('https://127.0.0.1:%d/video.html' % self.https_port)
            self.assertEqual(r['entries'][0]['url'], 'https://127.0.0.1:%d/vid.mp4' % self.https_port)

    def test_http_proxy(self):
        geo_proxy = '127.0.0.1:{0}'.format(self.geo_port)
        geo_proxy2 = 'localhost:{0}'.format(self.geo_port)  # ensure backend can support this format

        with self.make_ydl({
            'proxy': '127.0.0.1:{0}'.format(self.proxy_port),
            'geo_verification_proxy': geo_proxy,
        }) as ydl:
            url = 'http://foo.com/bar'
            response = ydl.urlopen(url).read().decode('utf-8')
            self.assertEqual(response, 'normal: {0}'.format(url))
            req = Request(url)
            req.add_header('Ytdl-request-proxy', geo_proxy2)
            response1 = ydl.urlopen(req).read().decode('utf-8')
            response2 = ydl.urlopen(Request(url, proxies={'http': geo_proxy})).read().decode('utf-8')
            self.assertEqual(response1, 'geo: {0}'.format(url))
            self.assertEqual(response2, 'geo: {0}'.format(url))
            # test that __noproxy__ disables all proxies for that request
            real_url = 'http://127.0.0.1:%d/headers' % self.http_port
            response3 = ydl.urlopen(
                Request(real_url, headers={'Ytdl-request-proxy': '__noproxy__'})).read().decode('utf-8')
            self.assertNotEqual(response3, f'normal: {real_url}')
            self.assertNotIn('Ytdl-request-proxy', response3)
            self.assertIn('Accept', response3)

    def test_http_proxy_with_idn(self):
        with self.make_ydl({
            'proxy': '127.0.0.1:{0}'.format(self.proxy_port),
        }) as ydl:
            url = 'http://中文.tw/'
            response = ydl.urlopen(url).read().decode('utf-8')
            # b'xn--fiq228c' is '中文'.encode('idna')
            self.assertEqual(response, 'normal: http://xn--fiq228c.tw/')

    def test_percent_encode(self):
        with self.make_ydl() as ydl:
            # Unicode characters should be encoded with uppercase percent-encoding
            res = ydl.urlopen(f'http://127.0.0.1:{self.http_port}/中文.html')
            self.assertEqual(res.status, 200)

            # don't normalize existing percent encodings
            res = ydl.urlopen(f'http://127.0.0.1:{self.http_port}/%c7%9f')
            self.assertEqual(res.status, 200)

    def test_unicode_path_redirection(self):
        with self.make_ydl(fake=False) as ydl:
            r = ydl.extract_info('http://127.0.0.1:%d/302-non-ascii-redirect' % self.http_port)
            self.assertEqual(r['entries'][0]['url'], 'http://127.0.0.1:%d/vid.mp4' % self.http_port)

    def test_raise_http_error(self):
        with self.make_ydl() as ydl:
            for bad_status in (400, 500, 599, 302):
                with self.assertRaises(HTTPError):
                    ydl.urlopen('http://127.0.0.1:%d/gen_%d' % (self.http_port, bad_status))

            # Should not raise an error
            ydl.urlopen('http://127.0.0.1:%d/gen_200' % self.http_port)

    def test_redirect_loop(self):
        with self.make_ydl() as ydl:
            with self.assertRaisesRegex(HTTPError, r'HTTP Error 301: Moved Permanently \(redirect loop detected\)'):
                ydl.urlopen('http://127.0.0.1:%d/redirect_loop' % self.http_port)

    def test_get_url(self):
        with self.make_ydl() as ydl:
            res = ydl.urlopen('http://127.0.0.1:%d/redirect_301' % self.http_port)
            self.assertEqual(res.url, 'http://127.0.0.1:%d/gen_204' % self.http_port)
            res2 = ydl.urlopen('http://127.0.0.1:%d/gen_200' % self.http_port)
            self.assertEqual(res2.url, 'http://127.0.0.1:%d/gen_200' % self.http_port)

    def test_redirect(self):
        # TODO
        with self.make_ydl() as ydl:
            # HEAD request. Should follow through with head request to gen_204 which should fail.
            with self.assertRaises(HTTPError):
                ydl.urlopen(HEADRequest('http://127.0.0.1:%d/redirect_301' % self.http_port))

            #res = ydl.urlopen('http://127.0.0.1:%d/redirect_301' % self.http_port)
            #self.assertEquals(res.method, 'GET')

    def test_incompleteread(self):
        with self.make_ydl({'socket_timeout': 2}) as ydl:
            with self.assertRaises(IncompleteRead):
                ydl.urlopen('http://127.0.0.1:%d/incompleteread' % self.http_port).read()

    def test_cookiejar(self):
        with self.make_ydl() as ydl:
            ydl.cookiejar.set_cookie(
                Cookie(
                    0, 'test', 'ytdlp', None, False, '127.0.0.1', True,
                    False, '/headers', True, False, None, False, None, None, {}))
            data = ydl.urlopen('http://127.0.0.1:%d/headers' % self.http_port).read()
            self.assertIn(b'Cookie: test=ytdlp', data)

    def test_request_types(self):
        with self.make_ydl() as ydl:
            url = 'http://127.0.0.1:%d/headers' % self.http_port
            test_header = {'X-ydl-test': '1'}
            # by url
            self.assertTrue(ydl.urlopen(url).read())

            # urllib Request compat and ydl Request
            for request in (urllib.request.Request(url, headers=test_header), Request(url, headers=test_header)):
                data = ydl.urlopen(request).read()
                self.assertIn(b'X-Ydl-Test: 1', data)

            with self.assertRaises(AssertionError):
                ydl.urlopen(None)

    def test_no_compression(self):
        with self.make_ydl() as ydl:
            url = 'http://127.0.0.1:%d/headers' % self.http_port
            for request in (Request(url, compression=False), Request(url, headers={'Youtubedl-no-compression': '1'})):
                data = ydl.urlopen(request).read()
                if b'Accept-Encoding' in data:
                    self.assertIn(b'Accept-Encoding: identity', data)

    def test_gzip_trailing_garbage(self):
        # https://github.com/ytdl-org/youtube-dl/commit/aa3e950764337ef9800c936f4de89b31c00dfcf5
        # https://github.com/ytdl-org/youtube-dl/commit/6f2ec15cee79d35dba065677cad9da7491ec6e6f
        with self.make_ydl() as ydl:
            data = ydl.urlopen('http://localhost:%d/trailing_garbage' % self.http_port).read().decode('utf-8')
            self.assertEqual(data, '<html><video src="/vid.mp4" /></html>')


def with_request_handlers(handlers=HTTP_TEST_BACKEND_HANDLERS):
    def inner_func(test):
        @functools.wraps(test)
        def wrapper(self, *args, **kwargs):
            for handler in handlers:
                if handler is None:
                    continue
                with self.subTest(handler=handler.__name__):
                    self.handler = handler
                    test(self, *args, **kwargs)
        return wrapper
    return inner_func


class TestClientCert(RequestHandlerTestBase, unittest.TestCase):
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

    @with_request_handlers()
    def _run_test(self, **params):
        with self.make_ydl({
            'logger': FakeLogger(),
            # Disable client-side validation of unacceptable self-signed testcert.pem
            # The test is of a check on the server side, so unaffected
            'nocheckcertificate': True,
            **params,
        }, fake=False) as ydl:
            r = ydl.extract_info('https://127.0.0.1:%d/video.html' % self.port)
            self.assertEqual(r['entries'][0]['url'], 'https://127.0.0.1:%d/vid.mp4' % self.port)

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


class TestUrllibRH(RequestHandlerCommonTestsBase, unittest.TestCase):
    handler = UrllibRH

    def test_ydl_compat_opener(self):
        ydl = self.make_ydl()
        res = ydl._opener.open('http://127.0.0.1:%d/gen_200' % self.http_port)
        self.assertIsInstance(res, http.client.HTTPResponse)


if __name__ == '__main__':
    unittest.main()
