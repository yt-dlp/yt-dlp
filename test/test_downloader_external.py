#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import http.cookiejar

from test.helper import FakeYDL
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
            self.assertNotIn('--load-cookies', downloader._make_cmd('test', TEST_INFO))
            # Test cookiejar tempfile arg is added
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            self.assertIn('--load-cookies', downloader._make_cmd('test', TEST_INFO))


class TestCurlFD(unittest.TestCase):
    def test_make_cmd(self):
        with FakeYDL() as ydl:
            downloader = CurlFD(ydl, {})
            self.assertNotIn('--cookie', downloader._make_cmd('test', TEST_INFO))
            # Test cookie header is added
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            self.assertIn('--cookie', downloader._make_cmd('test', TEST_INFO))
            self.assertIn('test=ytdlp', downloader._make_cmd('test', TEST_INFO))


class TestAria2cFD(unittest.TestCase):
    def test_make_cmd(self):
        with FakeYDL() as ydl:
            downloader = Aria2cFD(ydl, {})
            downloader._make_cmd('test', TEST_INFO)
            self.assertFalse(hasattr(downloader, '_cookies_tempfile'))

            # Test cookiejar tempfile arg is added
            ydl.cookiejar.set_cookie(http.cookiejar.Cookie(**TEST_COOKIE))
            cmd = downloader._make_cmd('test', TEST_INFO)
            self.assertIn(f'--load-cookies={downloader._cookies_tempfile}', cmd)


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
