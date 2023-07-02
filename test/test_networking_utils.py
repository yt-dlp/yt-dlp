#!/usr/bin/env python3

# Allow direct execution
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.error
import warnings
import platform
from yt_dlp.networking import Response
from yt_dlp.networking.exceptions import HTTPError, CompatHTTPError
import unittest
import io
import pytest

from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.networking.utils import InstanceStoreMixin, select_proxy, make_socks_proxy_opts
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


class TestNetworkingExceptions:

    @staticmethod
    def create_response(status):
        return Response(raw=io.BytesIO(b'test'), url='http://example.com', headers={'tesT': 'test'}, status=status)

    def test_http_error(self):

        response = self.create_response(403)
        error = HTTPError(response)

        assert error.status == 403
        assert str(error) == error.msg == 'HTTP Error 403: Forbidden'
        assert error.reason == response.reason
        assert error.response is response
        assert error.url == response.url
        assert 'test' in error.headers

        data = error.response.read()
        assert data == b'test'

    def test_compat_http(self):
        response = self.create_response(403)
        error = HTTPError(response)
        error_compat = CompatHTTPError(error)
        assert not isinstance(error, urllib.error.HTTPError)
        assert isinstance(error_compat, urllib.error.HTTPError)

        # These should not vive warnings
        assert error.status == 403
        assert str(error) == error.msg == 'HTTP Error 403: Forbidden'
        assert error.reason == response.reason
        assert error.response is response
        assert error.url == response.url
        assert 'test' in error.headers

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            assert error_compat.code == error_compat.getcode() == 403
            assert 'test' in error_compat.hdrs
            assert error_compat.hdrs is error_compat.info() is response.headers
            assert error_compat.filename == error_compat.geturl() == response.url
            assert isinstance(error_compat, urllib.error.HTTPError)
            data = error_compat.read()
            assert data == b'test'

    @pytest.mark.skipif(
        platform.python_implementation() == 'PyPy', reason='garbage collector works differently in pypy')
    def test_auto_close_http_error(self):
        res = self.create_response(404)
        HTTPError(res)
        assert res.raw.closed

        res = self.create_response(404)
        err = HTTPError(res)
        assert not res.raw.closed

    @pytest.mark.skipif(
        platform.python_implementation() == 'PyPy', reason='garbage collector works differently in pypy')
    def test_auto_close_compat_http_error(self):
        # should not close HTTPError
        res = self.create_response(404)
        err = HTTPError(res)
        CompatHTTPError(err)
        assert not res.closed

        # HTTPError should not close if compatHTTPError is in use
        res = self.create_response(404)
        err = CompatHTTPError(HTTPError(res))
        assert not res.closed

        # But it should close if compatHTTPError is not in use
        res = self.create_response(302)
        CompatHTTPError(HTTPError(res))
        assert res.closed

    def test_redirect_http_error(self):
        response = self.create_response(301)
        error = CompatHTTPError(HTTPError(response, redirect_loop=True))
        assert str(error) == 'HTTP Error 301: Moved Permanently (redirect loop detected)'


if __name__ == '__main__':
    unittest.main()
