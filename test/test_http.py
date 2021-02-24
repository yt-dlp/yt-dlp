#!/usr/bin/env python
# coding: utf-8
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import http_server_port
from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_http_server, compat_urllib_request
import ssl
import threading

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class HTTPTestRequestHandler(compat_http_server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/video.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><video src="/vid.mp4" /></html>')
        elif self.path == '/vid.mp4':
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.end_headers()
            self.wfile.write(b'\x00\x00\x00\x00\x20\x66\x74[video]')
        elif self.path == '/302':
            if sys.version_info[0] == 3:
                # XXX: Python 3 http server does not allow non-ASCII header values
                self.send_response(404)
                self.end_headers()
                return

            new_url = 'http://127.0.0.1:%d/中文.html' % http_server_port(self.server)
            self.send_response(302)
            self.send_header(b'Location', new_url.encode('utf-8'))
            self.end_headers()
        elif self.path == '/%E4%B8%AD%E6%96%87.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><video src="/vid.mp4" /></html>')
        else:
            assert False


class FakeLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class TestHTTP(unittest.TestCase):
    def setUp(self):
        self.httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def test_unicode_path_redirection(self):
        # XXX: Python 3 http server does not allow non-ASCII header values
        if sys.version_info[0] == 3:
            return

        ydl = YoutubeDL({'logger': FakeLogger()})
        r = ydl.extract_info('http://127.0.0.1:%d/302' % self.port)
        self.assertEqual(r['entries'][0]['url'], 'http://127.0.0.1:%d/vid.mp4' % self.port)


class TestHTTPS(unittest.TestCase):
    def setUp(self):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.httpd.socket = ssl.wrap_socket(
            self.httpd.socket, certfile=certfn, server_side=True)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def test_nocheckcertificate(self):
        if sys.version_info >= (2, 7, 9):  # No certificate checking anyways
            ydl = YoutubeDL({'logger': FakeLogger()})
            self.assertRaises(
                Exception,
                ydl.extract_info, 'https://127.0.0.1:%d/video.html' % self.port)

        ydl = YoutubeDL({'logger': FakeLogger(), 'nocheckcertificate': True})
        r = ydl.extract_info('https://127.0.0.1:%d/video.html' % self.port)
        self.assertEqual(r['entries'][0]['url'], 'https://127.0.0.1:%d/vid.mp4' % self.port)


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


class TestProxy(unittest.TestCase):
    def setUp(self):
        self.proxy = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('normal'))
        self.port = http_server_port(self.proxy)
        self.proxy_thread = threading.Thread(target=self.proxy.serve_forever)
        self.proxy_thread.daemon = True
        self.proxy_thread.start()

        self.geo_proxy = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('geo'))
        self.geo_port = http_server_port(self.geo_proxy)
        self.geo_proxy_thread = threading.Thread(target=self.geo_proxy.serve_forever)
        self.geo_proxy_thread.daemon = True
        self.geo_proxy_thread.start()

    def test_proxy(self):
        geo_proxy = '127.0.0.1:{0}'.format(self.geo_port)
        ydl = YoutubeDL({
            'proxy': '127.0.0.1:{0}'.format(self.port),
            'geo_verification_proxy': geo_proxy,
        })
        url = 'http://foo.com/bar'
        response = ydl.urlopen(url).read().decode('utf-8')
        self.assertEqual(response, 'normal: {0}'.format(url))

        req = compat_urllib_request.Request(url)
        req.add_header('Ytdl-request-proxy', geo_proxy)
        response = ydl.urlopen(req).read().decode('utf-8')
        self.assertEqual(response, 'geo: {0}'.format(url))

    def test_proxy_with_idn(self):
        ydl = YoutubeDL({
            'proxy': '127.0.0.1:{0}'.format(self.port),
        })
        url = 'http://中文.tw/'
        response = ydl.urlopen(url).read().decode('utf-8')
        # b'xn--fiq228c' is '中文'.encode('idna')
        self.assertEqual(response, 'normal: http://xn--fiq228c.tw/')


if __name__ == '__main__':
    unittest.main()
