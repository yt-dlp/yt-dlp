#!/usr/bin/env python3

# Allow direct execution
import io
import os
import random
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from email.message import Message
from http.cookiejar import CookieJar

import pytest

from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.networking.common import Request, HEADRequest, PUTRequest
from yt_dlp.networking.response import Response
from yt_dlp.networking.utils import InstanceStoreMixin, select_proxy, make_socks_proxy_opts
from yt_dlp.utils import CaseInsensitiveDict
from yt_dlp.socks import ProxyType

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestNetworkingUtils:

    def test_select_proxy(self):
        proxies = {
            'all': 'socks5://example.com',
            'http': 'http://example.com:1080',
            'no': 'bypass.example.com,yt-dl.org'
        }

        assert select_proxy('https://example.com', proxies) == proxies['all']
        assert select_proxy('http://example.com', proxies) == proxies['http']
        assert select_proxy('http://bypass.example.com', proxies) is None
        assert select_proxy('https://yt-dl.org', proxies) is None

    @pytest.mark.parametrize('socks_proxy,expected', [
        ('socks5h://example.com', {
            'proxytype': ProxyType.SOCKS5,
            'addr': 'example.com',
            'port': 1080,
            'rdns': True,
            'username': None,
            'password': None
        }),
        ('socks5://user:@example.com:5555', {
            'proxytype': ProxyType.SOCKS5,
            'addr': 'example.com',
            'port': 5555,
            'rdns': False,
            'username': 'user',
            'password': ''
        }),
        ('socks4://u%40ser:pa%20ss@127.0.0.1:1080', {
            'proxytype': ProxyType.SOCKS4,
            'addr': '127.0.0.1',
            'port': 1080,
            'rdns': False,
            'username': 'u@ser',
            'password': 'pa ss'
        }),
        ('socks4a://:pa%20ss@127.0.0.1', {
            'proxytype': ProxyType.SOCKS4A,
            'addr': '127.0.0.1',
            'port': 1080,
            'rdns': True,
            'username': '',
            'password': 'pa ss'
        })
    ])
    def test_make_socks_proxy_opts(self, socks_proxy, expected):
        assert make_socks_proxy_opts(socks_proxy) == expected

    def test_make_socks_proxy_unknown(self):
        with pytest.raises(ValueError, match='Unknown SOCKS proxy version: socks'):
            make_socks_proxy_opts('socks://127.0.0.1')


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

        self.assertNotEqual(
            mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'e', 4}}),
            mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}}))

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

    @pytest.mark.parametrize('reason,status,expected', [
        ('custom', 200, 'custom'),
        (None, 404, 'Not Found'),  # fallback status
        ('', 403, 'Forbidden'),
        (None, 999, None)
    ])
    def test_reason(self, reason, status, expected):
        res = Response(io.BytesIO(b''), url='test://', headers={}, status=status, reason=reason)
        assert res.reason == expected

    def test_headers(self):
        headers = Message()
        headers.add_header('Test', 'test')
        headers.add_header('Test', 'test2')
        headers.add_header('content-encoding', 'br')
        res = Response(io.BytesIO(b''), headers=headers, url='test://')
        assert res.headers.get_all('test') == ['test', 'test2']
        assert 'Content-Encoding' in res.headers

    def test_get_header(self):
        headers = Message()
        headers.add_header('Set-Cookie', 'cookie1')
        headers.add_header('Set-cookie', 'cookie2')
        headers.add_header('Test', 'test')
        headers.add_header('Test', 'test2')
        res = Response(io.BytesIO(b''), headers=headers, url='test://')
        assert res.get_header('test') == 'test, test2'
        assert res.get_header('set-Cookie') == 'cookie1'
        assert res.get_header('notexist', 'default') == 'default'

    def test_compat(self):
        res = Response(io.BytesIO(b''), url='test://', status=404, headers={'test': 'test'})
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            assert res.code == res.getcode() == res.status
            assert res.geturl() == res.url
            assert res.info() is res.headers
            assert res.getheader('test') == res.get_header('test')


if __name__ == '__main__':
    unittest.main()
