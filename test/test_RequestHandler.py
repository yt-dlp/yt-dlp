# Allow direct execution
import functools
import os
import subprocess
import sys
import unittest
from random import random

from yt_dlp.networking import UrllibRH, network_handlers
from yt_dlp.networking.common import Request, RHManager, UnsupportedRH, HEADRequest
from yt_dlp.utils import HTTPError, SSLError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import http_server_port, FakeYDL, is_download_test, get_params
from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_http_server
import ssl
import threading

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

REQUEST_HANDLERS = [UrllibRH]


class FakeLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class HTTPTestRequestHandler(compat_http_server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'  # required for persistent connections

    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        if self.path.startswith('/redirect'):
            self.send_response(303)
            self.send_header('Location', '/gen_204')
            self.end_headers()
        else:
            assert False

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
        elif self.path.startswith('/redirect'):
            self.send_response(301)
            self.send_header('Location', '/gen_204')
            self.send_header('Content-Length', '0')
            self.end_headers()
        else:
            assert False


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
    handler = UnsupportedRH

    def make_ydl(self, params=None, fake=True):
        ydl = (FakeYDL if fake else YoutubeDL)(params)
        ydl.default_session = ydl.make_RHManager([self.handler])
        return ydl


class RequestHandlerCommonTestsBase(RequestHandlerTestBase):
    def setUp(self):
        # HTTP server
        self.http_httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.http_port = http_server_port(self.http_httpd)
        self.http_server_thread = threading.Thread(target=self.http_httpd.serve_forever)
        self.http_server_thread.daemon = True
        self.http_server_thread.start()

        # HTTPS server
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.https_httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.https_httpd.socket = ssl.wrap_socket(
            self.https_httpd.socket, certfile=certfn, server_side=True)
        self.https_port = http_server_port(self.https_httpd)
        self.https_server_thread = threading.Thread(target=self.https_httpd.serve_forever)
        self.https_server_thread.daemon = True
        self.https_server_thread.start()

        # HTTP Proxy server
        self.proxy = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('normal'))
        self.proxy_port = http_server_port(self.proxy)
        self.proxy_thread = threading.Thread(target=self.proxy.serve_forever)
        self.proxy_thread.daemon = True
        self.proxy_thread.start()

        # Geo proxy server
        self.geo_proxy = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('geo'))
        self.geo_port = http_server_port(self.geo_proxy)
        self.geo_proxy_thread = threading.Thread(target=self.geo_proxy.serve_forever)
        self.geo_proxy_thread.daemon = True
        self.geo_proxy_thread.start()

    def test_nocheckcertificate(self):
        ydl = self.make_ydl({'logger': FakeLogger()})
        self.assertRaises(
            SSLError,
            ydl.urlopen, 'https://127.0.0.1:%d/video.html' % self.https_port)
        ydl = self.make_ydl({'logger': FakeLogger(), 'nocheckcertificate': True}, fake=False)
        r = ydl.extract_info('https://127.0.0.1:%d/video.html' % self.https_port)
        self.assertEqual(r['entries'][0]['url'], 'https://127.0.0.1:%d/vid.mp4' % self.https_port)

    def test_http_proxy(self):
        geo_proxy = '127.0.0.1:{0}'.format(self.geo_port)
        ydl = self.make_ydl({
            'proxy': '127.0.0.1:{0}'.format(self.proxy_port),
            'geo_verification_proxy': geo_proxy,
        })
        url = 'http://foo.com/bar'
        response = ydl.urlopen(url).read().decode('utf-8')
        self.assertEqual(response, 'normal: {0}'.format(url))
        req = Request(url)
        req.add_header('Ytdl-request-proxy', geo_proxy)
        response = ydl.urlopen(Request(url, proxy=geo_proxy)).read().decode('utf-8')
        self.assertEqual(response, 'geo: {0}'.format(url))

    def test_http_proxy_with_idn(self):
        ydl = self.make_ydl({
            'proxy': '127.0.0.1:{0}'.format(self.proxy_port),
        })
        url = 'http://中文.tw/'
        response = ydl.urlopen(url).read().decode('utf-8')
        # b'xn--fiq228c' is '中文'.encode('idna')
        self.assertEqual(response, 'normal: http://xn--fiq228c.tw/')

    def test_raise_http_error(self):
        ydl = self.make_ydl()
        for bad_status in (400, 500, 599, 302):
            with self.assertRaises(HTTPError):
                ydl.urlopen('http://127.0.0.1:%d/gen_%d' % (self.http_port, bad_status))

        # Should not raise an error
        ydl.urlopen('http://127.0.0.1:%d/gen_200' % self.http_port)

    def test_redirect_loop(self):
        ydl = self.make_ydl()
        with self.assertRaisesRegex(HTTPError, r'HTTP Error 301: Moved Permanently \(redirect loop detected\)'):
            ydl.urlopen('http://127.0.0.1:%d/redirect_loop' % self.http_port)

    def test_get_url(self):
        ydl = self.make_ydl()
        res = ydl.urlopen('http://127.0.0.1:%d/redirect' % self.http_port)
        res.read()
        self.assertEqual(res.url, 'http://127.0.0.1:%d/gen_204' % self.http_port)
        # TODO: rework redirect handlers
        res2 = ydl.urlopen(HEADRequest('http://127.0.0.1:%d/redirect' % self.http_port))
        a = res2.read()
        self.assertEqual(res2.url, 'http://127.0.0.1:%d/gen_204' % self.http_port)


def with_request_handlers(handlers=REQUEST_HANDLERS):
    def inner_func(test):
        @functools.wraps(test)
        def wrapper(self, *args, **kwargs):
            for handler in handlers:
                with self.subTest(handler=handler.__name__):
                    self.handler = handler
                    test(self, *args, **kwargs)
        return wrapper
    return inner_func


class TestUrllibRH(RequestHandlerCommonTestsBase, unittest.TestCase):
    handler = UrllibRH


if __name__ == '__main__':
    unittest.main()