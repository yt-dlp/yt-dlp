#!/usr/bin/env python3

# Allow direct execution
import io
import os
import random
import sys
import unittest
from http.cookiejar import CookieJar

import pytest

from networking import RequestHandler, Response
from yt_dlp.cookies import YoutubeDLCookieJar


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from yt_dlp.networking.utils import select_proxy, InstanceStoreMixin
from yt_dlp.networking.request import HEADRequest, PUTRequest, Request
from yt_dlp.utils import CaseInsensitiveDict

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestNetworkingUtils:

    def test_select_proxy(self):
        proxies = {
            'all': 'socks5://example.com',
            'http': 'http://example.com:1080',
        }

        assert select_proxy('https://example.com', proxies) ==  proxies['all']
        assert select_proxy('http://example.com', proxies) == proxies['http']


class TestRequest:

    def test_query(self):
        req = Request('http://example.com?q=something', query={'v': 'xyz'})
        assert req.url == 'http://example.com?q=something&v=xyz'

        req.update(query={'v': '123'})
        assert req.url == 'http://example.com?q=something&v=123'
        req.update(url='http://example.com', query={'v': 'xyz'})
        assert req.url == 'http://example.com?v=xyz'

    def test_method(self):
        req = Request('http://example.com')
        assert req.method == 'GET'
        req.data = b'test'
        assert req.method == 'POST'
        req.data = None
        assert req.method == 'GET'
        req.data = b'test2'
        req.method = 'PUT'
        assert req.method == 'PUT'
        req.data = None
        assert req.method == 'PUT'
        with pytest.raises(TypeError):
            req.method = 1

    def test_request_helpers(self):
        assert HEADRequest('http://example.com').method == 'HEAD'
        assert PUTRequest('http://example.com').method == 'PUT'

    def test_headers(self):
        req = Request('http://example.com', headers={'tesT': 'test'})
        assert req.headers == CaseInsensitiveDict({'test': 'test'})
        req.update(headers={'teSt2': 'test2'})
        assert req.headers == CaseInsensitiveDict({'test': 'test', 'test2': 'test2'})

        req.headers = new_headers = CaseInsensitiveDict({'test': 'test'})
        assert req.headers == CaseInsensitiveDict({'test': 'test'})
        assert req.headers is new_headers

        # test converts dict to case insensitive dict
        req.headers = new_headers = {'test2': 'test2'}
        assert isinstance(req.headers, CaseInsensitiveDict)
        assert req.headers is not new_headers

        with pytest.raises(TypeError):
            req.headers = None

    def test_data_type(self):
        req = Request('http://example.com')
        assert req.data is None
        # test bytes is allowed
        req.data = b'test'
        assert req.data == b'test'
        # test iterable of bytes is allowed
        i = [b'test', b'test2']
        req.data = i
        assert req.data == i

        # test file-like object is allowed
        f = io.BytesIO(b'test')
        req.data = f
        assert req.data == f

        # common mistake: test str not allowed
        with pytest.raises(TypeError):
            req.data = 'test'
        assert req.data != 'test'

        # common mistake: test dict is not allowed
        with pytest.raises(TypeError):
            req.data = {'test': 'test'}
        assert req.data != {'test': 'test'}

    def test_content_length_header(self):
        req = Request('http://example.com', headers={'Content-Length': '0'}, data=b'')
        assert req.headers.get('Content-Length') == '0'

        req.data = b'test'
        assert 'Content-Length' not in req.headers

        req = Request('http://example.com', headers={'Content-Length': '10'})
        assert 'Content-Length' not in req.headers

    def test_content_type_header(self):
        req = Request('http://example.com', headers={'Content-Type': 'test'}, data=b'test')
        assert req.headers.get('Content-Type') == 'test'
        req.data = b'test2'
        assert req.headers.get('Content-Type') == 'test'
        req.data = None
        assert 'Content-Type' not in req.headers
        req.data = b'test3'
        assert req.headers.get('Content-Type') == 'application/x-www-form-urlencoded'

    def test_proxies(self):
        req = Request(url='http://example.com', proxies={'http': 'http://127.0.0.1:8080'})
        assert req.proxies == {'http': 'http://127.0.0.1:8080'}
        with pytest.raises(TypeError):
            req.proxies = None

        req.proxies = {}
        assert req.proxies == {}

    def test_extensions(self):
        req = Request(url='http://example.com', extensions={'timeout': 2})
        assert req.extensions == {'timeout': 2}
        with pytest.raises(TypeError):
            req.extensions = None

        req.extensions = {}
        assert req.extensions == {}

        req.extensions['something'] = 'something'
        assert req.extensions == {'something': 'something'}

    def test_copy(self):
        req = Request(
            url='http://example.com',
            extensions={'cookiejar': CookieJar()},
            headers={'Accept-Encoding': 'br'},
            proxies={'http': 'http://127.0.0.1'},
            data=[b'123']
        )
        req_copy = req.copy()
        assert req_copy is not req
        assert req_copy.url == req.url
        assert req_copy.headers == req.headers
        assert req_copy.headers is not req.headers
        assert req_copy.proxies == req.proxies
        assert req_copy.proxies is not req.proxies

        # Data is not able to be copied
        assert req_copy.data == req.data
        assert req_copy.data is req.data

        # Shallow copy extensions
        assert req_copy.extensions is not req.extensions
        assert req_copy.extensions['cookiejar'] == req.extensions['cookiejar']

        # Subclasses are copied by default
        class AnotherRequest(Request):
            pass

        req = AnotherRequest(url='http://127.0.0.1')
        assert isinstance(req.copy(), AnotherRequest)

    def test_url(self):
        # test the url sanitization and escape
        pass


class TestInstanceStoreMixin(unittest.TestCase):

    class FakeInstanceStoreMixin(InstanceStoreMixin):
        def _create_instance(self, **kwargs):
            return random.randint(0, 1000000)

    def test_repo(self):
        mixin = self.FakeInstanceStoreMixin()
        self.assertEqual(
            mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}}),
            mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}}))

        # Nested dict is ignored
        self.assertEqual(
            mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'e', 4}}),
            mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}}))

        # But not the key
        self.assertNotEqual(
            mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}}),
            mixin._get_instance(d={'a': 1, 'b': 2, 'g': {'d', 4}}))

        self.assertEqual(
            mixin._get_instance(d={'a': 1}, e=[1, 2, 3]),
            mixin._get_instance(d={'a': 1}, e=[1, 2, 3]))

        self.assertNotEqual(
            mixin._get_instance(d={'a': 1}, e=[1, 2, 3]),
            mixin._get_instance(d={'a': 1}, e=[1, 2, 3, 4]))

        cookiejar = YoutubeDLCookieJar()
        self.assertEqual(
            mixin._get_instance(b=[1, 2], c=cookiejar),
            mixin._get_instance(b=[1, 2], c=cookiejar))

        self.assertNotEqual(
            mixin._get_instance(b=[1, 2], c=cookiejar),
            mixin._get_instance(b=[1, 2], c=YoutubeDLCookieJar()))

        # Different order
        self.assertEqual(
            mixin._get_instance(
                c=cookiejar, b=[1, 2]), mixin._get_instance(b=[1, 2], c=cookiejar))


class TestResponse:
    pass






if __name__ == '__main__':
    unittest.main()
