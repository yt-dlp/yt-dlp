#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import http.server
import ssl
import threading
import urllib.request

from test.helper import http_server_port
from yt_dlp import YoutubeDL

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class HTTPTestRequestHandler(http.server.BaseHTTPRequestHandler):
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
        elif self.path == '/%E4%B8%AD%E6%96%87.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><video src="/vid.mp4" /></html>')
        else:
            assert False


class FakeLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class TestHTTP(unittest.TestCase):
    def setUp(self):
        self.httpd = http.server.HTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()


class TestHTTPS(unittest.TestCase):
    def setUp(self):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.httpd = http.server.HTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.load_cert_chain(certfn, None)
        self.httpd.socket = sslctx.wrap_socket(self.httpd.socket, server_side=True)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def test_nocheckcertificate(self):
        ydl = YoutubeDL({'logger': FakeLogger()})
        self.assertRaises(
            Exception,
            ydl.extract_info, 'https://127.0.0.1:%d/video.html' % self.port)

        ydl = YoutubeDL({'logger': FakeLogger(), 'nocheckcertificate': True})
        r = ydl.extract_info('https://127.0.0.1:%d/video.html' % self.port)
        self.assertEqual(r['url'], 'https://127.0.0.1:%d/vid.mp4' % self.port)


class TestClientCert(unittest.TestCase):
    def setUp(self):
        certfn = os.path.join(TEST_DIR, 'testcert.pem')
        self.certdir = os.path.join(TEST_DIR, 'testdata', 'certificate')
        cacertfn = os.path.join(self.certdir, 'ca.crt')
        self.httpd = http.server.HTTPServer(('127.0.0.1', 0), HTTPTestRequestHandler)
        sslctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sslctx.verify_mode = ssl.CERT_REQUIRED
        sslctx.load_verify_locations(cafile=cacertfn)
        sslctx.load_cert_chain(certfn, None)
        self.httpd.socket = sslctx.wrap_socket(self.httpd.socket, server_side=True)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def _run_test(self, **params):
        ydl = YoutubeDL({
            'logger': FakeLogger(),
            # Disable client-side validation of unacceptable self-signed testcert.pem
            # The test is of a check on the server side, so unaffected
            'nocheckcertificate': True,
            **params,
        })
        r = ydl.extract_info('https://127.0.0.1:%d/video.html' % self.port)
        self.assertEqual(r['url'], 'https://127.0.0.1:%d/vid.mp4' % self.port)

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


def _build_proxy_handler(name):
    class HTTPTestRequestHandler(http.server.BaseHTTPRequestHandler):
        proxy_name = name

        def log_message(self, format, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f'{self.proxy_name}: {self.path}'.encode())
    return HTTPTestRequestHandler


class TestProxy(unittest.TestCase):
    def setUp(self):
        self.proxy = http.server.HTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('normal'))
        self.port = http_server_port(self.proxy)
        self.proxy_thread = threading.Thread(target=self.proxy.serve_forever)
        self.proxy_thread.daemon = True
        self.proxy_thread.start()

        self.geo_proxy = http.server.HTTPServer(
            ('127.0.0.1', 0), _build_proxy_handler('geo'))
        self.geo_port = http_server_port(self.geo_proxy)
        self.geo_proxy_thread = threading.Thread(target=self.geo_proxy.serve_forever)
        self.geo_proxy_thread.daemon = True
        self.geo_proxy_thread.start()

    def test_proxy(self):
        geo_proxy = f'127.0.0.1:{self.geo_port}'
        ydl = YoutubeDL({
            'proxy': f'127.0.0.1:{self.port}',
            'geo_verification_proxy': geo_proxy,
        })
        url = 'http://foo.com/bar'
        response = ydl.urlopen(url).read().decode()
        self.assertEqual(response, f'normal: {url}')

        req = urllib.request.Request(url)
        req.add_header('Ytdl-request-proxy', geo_proxy)
        response = ydl.urlopen(req).read().decode()
        self.assertEqual(response, f'geo: {url}')

    def test_proxy_with_idn(self):
        ydl = YoutubeDL({
            'proxy': f'127.0.0.1:{self.port}',
        })
        url = 'http://中文.tw/'
        response = ydl.urlopen(url).read().decode()
        # b'xn--fiq228c' is '中文'.encode('idna')
        self.assertEqual(response, 'normal: http://xn--fiq228c.tw/')


if __name__ == '__main__':
    unittest.main()
