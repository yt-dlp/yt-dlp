#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import re
import tempfile

from yt_dlp.cookies import YoutubeDLCookieJar


class TestYoutubeDLCookieJar(unittest.TestCase):
    def test_keep_session_cookies(self):
        cookiejar = YoutubeDLCookieJar('./test/testdata/cookies/session_cookies.txt')
        cookiejar.load()
        tf = tempfile.NamedTemporaryFile(delete=False)
        try:
            cookiejar.save(filename=tf.name)
            temp = tf.read().decode()
            self.assertTrue(re.search(
                r'www\.foobar\.foobar\s+FALSE\s+/\s+TRUE\s+0\s+YoutubeDLExpiresEmpty\s+YoutubeDLExpiresEmptyValue', temp))
            self.assertTrue(re.search(
                r'www\.foobar\.foobar\s+FALSE\s+/\s+TRUE\s+0\s+YoutubeDLExpires0\s+YoutubeDLExpires0Value', temp))
        finally:
            tf.close()
            os.remove(tf.name)

    def test_strip_httponly_prefix(self):
        cookiejar = YoutubeDLCookieJar('./test/testdata/cookies/httponly_cookies.txt')
        cookiejar.load()

        def assert_cookie_has_value(key):
            self.assertEqual(cookiejar._cookies['www.foobar.foobar']['/'][key].value, key + '_VALUE')

        assert_cookie_has_value('HTTPONLY_COOKIE')
        assert_cookie_has_value('JS_ACCESSIBLE_COOKIE')

    def test_malformed_cookies(self):
        cookiejar = YoutubeDLCookieJar('./test/testdata/cookies/malformed_cookies.txt')
        cookiejar.load()
        # Cookies should be empty since all malformed cookie file entries
        # will be ignored
        self.assertFalse(cookiejar._cookies)

    def test_get_cookie_header(self):
        cookiejar = YoutubeDLCookieJar('./test/testdata/cookies/httponly_cookies.txt')
        cookiejar.load()
        header = cookiejar.get_cookie_header('https://www.foobar.foobar')
        self.assertIn('HTTPONLY_COOKIE', header)

    def test_get_cookies_for_url(self):
        cookiejar = YoutubeDLCookieJar('./test/testdata/cookies/session_cookies.txt')
        cookiejar.load()
        cookies = cookiejar.get_cookies_for_url('https://www.foobar.foobar/')
        self.assertEqual(len(cookies), 2)
        cookies = cookiejar.get_cookies_for_url('https://foobar.foobar/')
        self.assertFalse(cookies)


if __name__ == '__main__':
    unittest.main()
