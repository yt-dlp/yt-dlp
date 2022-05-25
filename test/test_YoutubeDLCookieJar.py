#!/usr/bin/env python3
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.utils import YoutubeDLCookieJar


class TestYoutubeDLCookieJar(unittest.TestCase):
    def test_keep_session_cookies(self):
        cookiejar = YoutubeDLCookieJar('./test/testdata/cookies/session_cookies.txt')
        cookiejar.load(ignore_discard=True, ignore_expires=True)
        tf = tempfile.NamedTemporaryFile(delete=False)
        try:
            cookiejar.save(filename=tf.name, ignore_discard=True, ignore_expires=True)
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
        cookiejar.load(ignore_discard=True, ignore_expires=True)

        def assert_cookie_has_value(key):
            self.assertEqual(cookiejar._cookies['www.foobar.foobar']['/'][key].value, key + '_VALUE')

        assert_cookie_has_value('HTTPONLY_COOKIE')
        assert_cookie_has_value('JS_ACCESSIBLE_COOKIE')

    def test_malformed_cookies(self):
        cookiejar = YoutubeDLCookieJar('./test/testdata/cookies/malformed_cookies.txt')
        cookiejar.load(ignore_discard=True, ignore_expires=True)
        # Cookies should be empty since all malformed cookie file entries
        # will be ignored
        self.assertFalse(cookiejar._cookies)


if __name__ == '__main__':
    unittest.main()
