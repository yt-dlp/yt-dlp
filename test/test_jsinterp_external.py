#!/usr/bin/env python3

from __future__ import annotations
import os
import dataclasses
import datetime
import time
import sys
import unittest
import http.cookiejar


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import (
    FakeYDL,
)
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.jsinterp.common import ExternalJSI
from yt_dlp.jsinterp._deno import DenoJSI, DenoJITlessJSI, DenoJSDomJSI
from yt_dlp.jsinterp._phantomjs import PhantomJSJSI


@dataclasses.dataclass
class NetscapeFields:
    name: str
    value: str
    domain: str
    path: str
    secure: bool
    expires: int | None

    def to_cookie(self):
        return http.cookiejar.Cookie(
            0, self.name, self.value,
            None, False,
            self.domain, True, self.domain.startswith('.'),
            self.path, True,
            self.secure, self.expires, False,
            None, None, {},
        )

    def expire_str(self):
        return datetime.datetime.fromtimestamp(
            self.expires, datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

    def __eq__(self, other: NetscapeFields | http.cookiejar.Cookie):
        return all(getattr(self, attr) == getattr(other, attr) for attr in ['name', 'value', 'domain', 'path', 'secure', 'expires'])


class Base:
    class TestExternalJSI(unittest.TestCase):
        _JSI_CLASS: type[ExternalJSI] = None
        maxDiff = 2000

        def setUp(self):
            self.ydl = FakeYDL()
            self.jsi = self._JSI_CLASS(self.ydl, 19, {})
            if not self.jsi_available():
                self.skipTest('Not available')

        def jsi_available(self):
            return self._JSI_CLASS and self._JSI_CLASS.exe_version

        def test_execute(self):
            self.assertEqual(self.jsi.execute('console.log("Hello, world!");'), 'Hello, world!')

        def test_execute_dom_parse(self):
            if 'dom' not in self.jsi._SUPPORTED_FEATURES:
                self.skipTest('DOM not supported')
            self.assertEqual(self.jsi.execute(
                'console.log(document.getElementById("test-div").innerHTML);',
                location='https://example.com',
                html='<html><body><div id="test-div">Hello, world!</div></body></html>'),
                'Hello, world!')

        def test_execute_dom_script(self):
            if 'dom' not in self.jsi._SUPPORTED_FEATURES:
                self.skipTest('DOM not supported')
            self.assertEqual(self.jsi.execute(
                'console.log(document.getElementById("test-div").innerHTML);',
                location='https://example.com',
                html='''<html><body>
                    <div id="test-div"></div>
                    <script src="https://example.com/script.js"></script>
                    <script type="text/javascript">
                        document.getElementById("test-div").innerHTML = "Hello, world!"
                        console.log('this should not show up');
                    </script>
                </body></html>'''),
                'Hello, world!')

        def test_execute_dom_script_with_error(self):
            if 'dom' not in self.jsi._SUPPORTED_FEATURES:
                self.skipTest('DOM not supported')
            self.assertEqual(self.jsi.execute(
                'console.log(document.getElementById("test-div").innerHTML);',
                location='https://example.com',
                html='''<html><body>
                    <div id="test-div"></div>
                    <script src="https://example.com/script.js"></script>
                    <script type="text/javascript">
                        document.getElementById("test-div").innerHTML = "Hello, world!"
                        console.log('this should not show up');
                        a = b; // Undefined variable assignment
                    </script>
                </body></html>'''),
                'Hello, world!')

        def assert_cookiejar_equal(self, cookiejar: http.cookiejar.CookieJar, ref_cookiejar: http.cookiejar.CookieJar):
            for cookie in cookiejar:
                ref_cookie = next((c for c in ref_cookiejar if c.name == cookie.name and c.domain == cookie.domain), None)
                self.assertEqual(repr(cookie), repr(ref_cookie))

        def assert_cookie_str_equal(self, cookie_str, ref_cookie_str):
            print([cookie_str, ref_cookie_str])
            self.assertEqual(set(cookie_str.split('; ')), set(ref_cookie_str.split('; ')))

        def test_execute_cookiejar(self):
            if 'cookies' not in self.jsi._SUPPORTED_FEATURES:
                self.skipTest('Cookies not supported')
            cookiejar = YoutubeDLCookieJar()
            ref_cookiejar = YoutubeDLCookieJar()
            for test_cookie in [
                NetscapeFields('test1', 'test1', '.example.com', '/', False, int(time.time()) + 1000),
                NetscapeFields('test2', 'test2', '.example.com', '/', True, int(time.time()) + 1000),
                NetscapeFields('test3', 'test3', '.example.com', '/123', False, int(time.time()) + 1000),
                NetscapeFields('test4', 'test4', '.example.com', '/456', False, int(time.time()) + 1000),
                NetscapeFields('test5', 'test5', '.example.com', '/123', True, int(time.time()) + 1000),
                NetscapeFields('test6', 'test6', '.example.com', '/456', True, int(time.time()) + 1000),
                NetscapeFields('test1', 'other1', '.other.com', '/', False, int(time.time()) + 1000),
                NetscapeFields('test2', 'other2', '.other.com', '/', False, int(time.time()) + 1000),
                NetscapeFields('test7', 'other7', '.other.com', '/', False, int(time.time()) + 1000),
            ]:
                cookiejar.set_cookie(test_cookie.to_cookie())
                ref_cookiejar.set_cookie(test_cookie.to_cookie())

            # test identity without modification from js
            self.assert_cookie_str_equal(self.jsi.execute(
                'console.log(document.cookie);',
                location='http://example.com/123/456',
                html='<html><body><div id="test-div">Hello, world!</div></body></html>',
                cookiejar=cookiejar),
                'test1=test1; test3=test3')
            self.assert_cookiejar_equal(cookiejar, ref_cookiejar)

            # test modification of existing cookie from js
            new_cookie_1 = NetscapeFields('test1', 'new1', '.example.com', '/', True, int(time.time()) + 900)
            new_cookie_2 = NetscapeFields('test2', 'new2', '.example.com', '/', True, int(time.time()) + 900)
            ref_cookiejar.set_cookie(new_cookie_1.to_cookie())
            ref_cookiejar.set_cookie(new_cookie_2.to_cookie())
            self.assert_cookie_str_equal(self.jsi.execute(
                f'''document.cookie = "test1=new1; secure; expires={new_cookie_1.expire_str()}; domain=.example.com; path=/";
                console.log(document.cookie);''',
                location='https://example.com/123/456',
                html=f'''<html><body><div id="test-div">Hello, world!</div>
                    <script>
                        document.cookie = "test2=new2; secure; expires={new_cookie_2.expire_str()}; domain=.example.com; path=/";
                    </script>
                </body></html>''',
                cookiejar=cookiejar),
                'test1=new1; test2=new2; test3=test3; test5=test5')
            self.assert_cookiejar_equal(cookiejar, ref_cookiejar)


class TestDeno(Base.TestExternalJSI):
    _JSI_CLASS = DenoJSI


class TestDenoJITless(Base.TestExternalJSI):
    _JSI_CLASS = DenoJITlessJSI


class TestDenoDom(Base.TestExternalJSI):
    _JSI_CLASS = DenoJSDomJSI


class TestPhantomJS(Base.TestExternalJSI):
    _JSI_CLASS = PhantomJSJSI


if __name__ == '__main__':
    unittest.main()
