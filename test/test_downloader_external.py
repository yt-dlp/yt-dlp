#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import http.cookiejar
import http.server
import ipaddress
import pytest
import json
import tempfile
import threading

from test.helper import FakeYDL
from yt_dlp.networking.common import HTTPHeaderDict
from yt_dlp.downloader.external import (
    Aria2cFD,
    AxelFD,
    CurlFD,
    FFmpegFD,
    HttpieFD,
    WgetFD,
)

TEST_COOKIE = {
    'version': 0,
    'name': 'test',
    'value': 'ytdlp',
    'port': None,
    'port_specified': False,
    'domain': '.example.com',
    'domain_specified': True,
    'domain_initial_dot': False,
    'path': '/',
    'path_specified': True,
    'secure': False,
    'expires': None,
    'discard': False,
    'comment': None,
    'comment_url': None,
    'rest': {},
}

TEST_INFO = {'url': 'http://www.example.com/'}


class TestHttpieFD(unittest.TestCase):
    def test_make_cmd(self):
        with FakeYDL() as ydl:
            downloader = HttpieFD(ydl, {})
            self.assertEqual(
                downloader._make_cmd('test', TEST_INFO),
                ['http', '--download', '--output', 'test', 'http://www.example.com/'])

            # Test cookie header is added
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            self.assertEqual(
                downloader._make_cmd('test', TEST_INFO),
                ['http', '--download', '--output', 'test', 'http://www.example.com/', 'Cookie:test=ytdlp'])


class TestAxelFD(unittest.TestCase):
    def test_make_cmd(self):
        with FakeYDL() as ydl:
            downloader = AxelFD(ydl, {})
            self.assertEqual(
                downloader._make_cmd('test', TEST_INFO),
                ['axel', '-o', 'test', '--', 'http://www.example.com/'])

            # Test cookie header is added
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            self.assertEqual(
                downloader._make_cmd('test', TEST_INFO),
                ['axel', '-o', 'test', '-H', 'Cookie: test=ytdlp', '--max-redirect=0', '--', 'http://www.example.com/'])


class TestWgetFD(unittest.TestCase):
    def test_make_cmd(self):
        with FakeYDL() as ydl:
            downloader = WgetFD(ydl, {})
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            assert '--load-cookies' in downloader._make_cmd('test', TEST_INFO)


class HTTPTestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self, /):
        if self.path.startswith('/redirect'):
            target = self.headers.get('X-Redirect-Location')
            if not target:
                self.send_error(500)
                return
            self.send_response(301)
            self.send_header('Location', target)
            self.end_headers()

        elif self.path == '/headers':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(list(self.headers.items())).encode())


class HTTPTestServer(http.server.HTTPServer):
    @property
    def address(self, /):
        return ipaddress.ip_address(self.server_address[0])

    @property
    def uri(self, /):
        addr, port, *_ = self.server_address
        if ':' in addr:
            addr = f'[{addr}]'
        return f'http://{addr}:{port}'

    def __enter__(self, /):
        result = super().__enter__()
        thread = threading.Thread(target=self.serve_forever)
        thread.start()
        return result

    def __exit__(self, /, *exc):
        self.shutdown()
        return super().__exit__(*exc)


class TestDownloaderCookieBehavior:
    @pytest.mark.parametrize('downloader_cls', [
        pytest.param(CurlFD, marks=pytest.mark.skipif(not CurlFD.available() or CurlFD._curl_version < CurlFD._MIN_VERSION_FOR_STDIN_COOKIES, reason='curl unavailable or too old')),
        pytest.param(WgetFD, marks=pytest.mark.skipif(not WgetFD.available(), reason='wget unavailable')),
        pytest.param(Aria2cFD, marks=pytest.mark.skipif(not Aria2cFD.available(), reason='aria2c unavailable')),
    ])
    def test_cookie_behavior(self, /, downloader_cls):
        with FakeYDL() as ydl:
            downloader = downloader_cls(ydl, {})

            with HTTPTestServer(('localhost', 0), HTTPTestHandler) as server_a:
                second_addr = server_a.address + 1
                if not second_addr.is_loopback:
                    second_addr = server_a.address - 1
                assert second_addr.is_loopback, f'failed to find derived loopback address for {server_a.address}'

                ydl.cookiejar.set_cookie(http.cookiejar.Cookie(
                    1,
                    'c',
                    'test',
                    server_a.server_address[1],
                    True,
                    str(server_a.address),
                    True,
                    False,
                    '/',
                    False,
                    False,
                    0,
                    True,
                    None,
                    None,
                    {},
                ))

                with tempfile.NamedTemporaryFile(delete=False) as file:
                    file.close()
                    assert downloader.real_download(file.name, {'url': f'{server_a.uri}/headers'}), 'Expected download (/headers) to succeed'

                    with open(file.name, 'rb') as f:
                        data = HTTPHeaderDict(json.load(f))
                    assert 'c=test' in data.get('Cookie', '').split(';'), 'Expected cookie to be set in initial request'

                    with HTTPTestServer((str(second_addr), 0), HTTPTestHandler) as server_b:
                        assert downloader.real_download(file.name, {
                            'url': f'{server_a.uri}/redirect',
                            'http_headers': {
                                'X-Redirect-Location': f'{server_b.uri}/headers',
                            },
                        }), 'Expected download (/redirect) to succeed'

                        with open(file.name, 'rb') as f:
                            data = HTTPHeaderDict(json.load(f))

        assert data.get('Cookie') is None, 'Expected cookie to be unset in redirected request'


class TestAria2cFD(unittest.TestCase):
    def test_make_cmd(self):
        with FakeYDL() as ydl:
            downloader = Aria2cFD(ydl, {})
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            cmd = downloader._make_cmd('test', TEST_INFO)
            assert f'--load-cookies={downloader._cookies_tempfile}' in cmd


@unittest.skipUnless(FFmpegFD.available(), 'ffmpeg not found')
class TestFFmpegFD(unittest.TestCase):
    _args = []

    def _test_cmd(self, args):
        self._args = args

    def test_make_cmd(self):
        with FakeYDL() as ydl:
            downloader = FFmpegFD(ydl, {})
            downloader._debug_cmd = self._test_cmd

            downloader._call_downloader('test', {**TEST_INFO, 'ext': 'mp4'})
            self.assertEqual(self._args, [
                'ffmpeg', '-y', '-hide_banner', '-i', 'http://www.example.com/',
                '-c', 'copy', '-f', 'mp4', 'file:test'])

            # Test cookies arg is added
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            downloader._call_downloader('test', {**TEST_INFO, 'ext': 'mp4'})
            self.assertEqual(self._args, [
                'ffmpeg', '-y', '-hide_banner', '-cookies', 'test=ytdlp; path=/; domain=.example.com;\r\n',
                '-i', 'http://www.example.com/', '-c', 'copy', '-f', 'mp4', 'file:test'])

            # Test with non-url input (ffmpeg reads from stdin '-' for websockets)
            downloader._call_downloader('test', {'url': 'x', 'ext': 'mp4'})
            self.assertEqual(self._args, [
                'ffmpeg', '-y', '-hide_banner', '-i', 'x', '-c', 'copy', '-f', 'mp4', 'file:test'])


if __name__ == '__main__':
    unittest.main()
