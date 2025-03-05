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
from yt_dlp.utils import (
    variadic,
)
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.jsinterp import _JSI_HANDLERS
assert set(_JSI_HANDLERS) == {'Deno', 'DenoJSDom', 'PhantomJS'}
from yt_dlp.jsinterp.common import ExternalJSI, _ALL_FEATURES
from yt_dlp.jsinterp._deno import DenoJSI, DenoJSDomJSI
from yt_dlp.jsinterp._phantomjs import PhantomJSJSI
from yt_dlp.jsinterp._helper import prepare_wasm_jsmodule


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


covered_features = set()


def requires_feature(features):
    covered_features.update(variadic(features))

    def outer(func):
        def wrapper(self, *args, **kwargs):
            if not self.jsi._SUPPORTED_FEATURES.issuperset(variadic(features)):
                print(f'{self._JSI_CLASS.__name__} does not support {features!r}, skipping')
                self.skipTest(f'{"&".join(variadic(features))} not supported')
            return func(self, *args, **kwargs)
        return wrapper
    return outer


class Base:
    class TestExternalJSI(unittest.TestCase):
        _JSI_CLASS: type[ExternalJSI] = None
        _TESTDATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata', 'jsi_external')
        maxDiff = 2000

        def setUp(self):
            print()
            self.ydl = FakeYDL()
            self.url_param = ''
            if not self._JSI_CLASS.exe_version:
                print(f'{self._JSI_CLASS.__name__} is not installed, skipping')
                self.skipTest('Not available')

        @property
        def jsi(self):
            return self._JSI_CLASS(self.ydl, self.url_param, 10, {})

        def test_execute(self):
            self.assertEqual(self.jsi.execute('console.log("Hello, world!");'), 'Hello, world!')

        def test_user_agent(self):
            ua = self.ydl.params['http_headers']['User-Agent']
            self.assertEqual(self.jsi.execute('console.log(navigator.userAgent);'), ua)
            self.assertNotEqual(self.jsi.execute('console.log(JSON.stringify(navigator.webdriver));'), 'true')

            jsi = self._JSI_CLASS(self.ydl, self.url_param, 10, {}, user_agent='test/ua')
            self.assertEqual(jsi.execute('console.log(navigator.userAgent);'), 'test/ua')

        @requires_feature('location')
        def test_location(self):
            self.url_param = 'https://example.com/123/456'
            self.assertEqual(self.jsi.execute('console.log(JSON.stringify([location.href, location.hostname]));'),
                             '["https://example.com/123/456","example.com"]')

        @requires_feature('dom')
        def test_execute_dom_parse(self):
            self.assertEqual(self.jsi.execute(
                'console.log(document.getElementById("test-div").innerHTML);',
                html='<html><body><div id="test-div">Hello, world!</div></body></html>'),
                'Hello, world!')

        @requires_feature('dom')
        def test_execute_dom_script(self):
            self.assertEqual(self.jsi.execute(
                'console.log(document.getElementById("test-div").innerHTML);',
                html='''<html><head><title>Hello, world!</title><body>
                    <div id="test-div"></div>
                    <script src="https://example.com/script.js"></script>
                    <script type="text/javascript">
                        document.getElementById("test-div").innerHTML = document.title;
                        console.log('this should not show up');
                        a = b; // Errors should be ignored
                    </script>
                </body></html>'''),
                'Hello, world!')

        @requires_feature(['dom', 'location'])
        def test_dom_location(self):
            self.url_param = 'https://example.com/123/456'
            self.assertEqual(self.jsi.execute(
                'console.log(document.getElementById("test-div").innerHTML);',
                html='''<html><head><script>
                document.querySelector("#test-div").innerHTML = document.domain</script></head>
                <body><div id="test-div">Hello, world!</div></body></html>'''),
                'example.com')

        @requires_feature('cookies')
        def test_execute_cookiejar(self):
            cookiejar = YoutubeDLCookieJar()
            ref_cookiejar = YoutubeDLCookieJar()

            def _assert_expected_execute(cookie_str, ref_cookie_str):
                self.assertEqual(set(cookie_str.split('; ')), set(ref_cookie_str.split('; ')))
                for cookie in cookiejar:
                    ref_cookie = next((c for c in ref_cookiejar if c.name == cookie.name
                                       and c.domain == cookie.domain), None)
                    self.assertEqual(repr(cookie), repr(ref_cookie))

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
            self.url_param = 'http://example.com/123/456'
            _assert_expected_execute(self.jsi.execute(
                'console.log(document.cookie);', cookiejar=cookiejar),
                'test1=test1; test3=test3')

            # test modification of existing cookie from js
            new_cookie_1 = NetscapeFields('test1', 'new1', '.example.com', '/', True, int(time.time()) + 900)
            new_cookie_2 = NetscapeFields('test2', 'new2', '.example.com', '/', True, int(time.time()) + 900)
            ref_cookiejar.set_cookie(new_cookie_1.to_cookie())
            ref_cookiejar.set_cookie(new_cookie_2.to_cookie())
            self.url_param = 'https://example.com/123/456'
            _assert_expected_execute(self.jsi.execute(
                f'''document.cookie = "test1=new1; secure; expires={new_cookie_1.expire_str()}; domain=.example.com; path=/";
                console.log(document.cookie);''',
                html=f'''<html><body><div id="test-div">Hello, world!</div>
                    <script>
                        document.cookie = "test2=new2; secure; expires={new_cookie_2.expire_str()}; domain=.example.com; path=/";
                    </script>
                </body></html>''',
                cookiejar=cookiejar),
                'test1=new1; test2=new2; test3=test3; test5=test5')

        @requires_feature('wasm')
        def test_wasm(self):
            with open(os.path.join(self._TESTDATA_DIR, 'hello_wasm.js')) as f:
                js_mod = f.read()
            with open(os.path.join(self._TESTDATA_DIR, 'hello_wasm_bg.wasm'), 'rb') as f:
                wasm = f.read()

            js_base = prepare_wasm_jsmodule(js_mod, wasm)

            js_code = js_base + ''';
            console.log(add(1, 2));
            greet('world');
            '''

            self.assertEqual(self.jsi.execute(js_code), '3\nHello, world!')


class TestDeno(Base.TestExternalJSI):
    _JSI_CLASS = DenoJSI


class TestDenoDom(Base.TestExternalJSI):
    _JSI_CLASS = DenoJSDomJSI


class TestPhantomJS(Base.TestExternalJSI):
    _JSI_CLASS = PhantomJSJSI


expect_covered_features = set(_ALL_FEATURES)
assert covered_features.issuperset(expect_covered_features), f'Missing tests for features: {expect_covered_features - covered_features}'

if __name__ == '__main__':
    unittest.main()
