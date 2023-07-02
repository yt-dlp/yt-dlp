#!/usr/bin/env python3

# Allow direct execution
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contextlib
import urllib.error
import warnings
import platform
from yt_dlp.networking import Response
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import CompatHTTPError
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

    @pytest.mark.parametrize('http_error_class', [HTTPError, lambda r: CompatHTTPError(HTTPError(r))])
    def test_http_error(self, http_error_class):

        response = self.create_response(403)
        error = http_error_class(response)

        assert error.status == 403
        assert str(error) == error.msg == 'HTTP Error 403: Forbidden'
        assert error.reason == response.reason
        assert error.response is response

        data = error.response.read()
        assert data == b'test'
        assert repr(error) == '<HTTPError 403: Forbidden>'

    @pytest.mark.parametrize('http_error_class', [HTTPError, lambda *args, **kwargs: CompatHTTPError(HTTPError(*args, **kwargs))])
    def test_redirect_http_error(self, http_error_class):
        response = self.create_response(301)
        error = http_error_class(response, redirect_loop=True)
        assert str(error) == error.msg == 'HTTP Error 301: Moved Permanently (redirect loop detected)'
        assert error.reason == 'Moved Permanently'

    def test_compat_http(self):
        response = self.create_response(403)
        error = CompatHTTPError(HTTPError(response))
        assert isinstance(error, HTTPError)
        assert isinstance(error, urllib.error.HTTPError)

        @contextlib.contextmanager
        def raises_deprecation_warning():
            with warnings.catch_warnings(record=True) as w:
                yield

                if len(w) == 0:
                    pytest.fail('Did not raise DeprecationWarning')
                if len(w) > 1:
                    pytest.fail(f'Raised multiple warnings: {w}')

                if not issubclass(w[-1].category, DeprecationWarning):
                    pytest.fail(f'Expected DeprecationWarning, got {w[-1].category}')
                w.clear()

        with raises_deprecation_warning():
            assert error.code == 403

        with raises_deprecation_warning():
            assert error.getcode() == 403

        with raises_deprecation_warning():
            assert error.hdrs is error.response.headers

        with raises_deprecation_warning():
            assert error.info() is error.response.headers

        with raises_deprecation_warning():
            assert error.headers is error.response.headers

        with raises_deprecation_warning():
            assert error.filename == error.response.url

        with raises_deprecation_warning():
            assert error.url == error.response.url

        with raises_deprecation_warning():
            assert error.geturl() == error.response.url

        # Passthrough file operations
        with raises_deprecation_warning():
            assert error.read() == b'test'

        with raises_deprecation_warning():
            assert not error.closed

        with raises_deprecation_warning():
            # Technically Response operations are also passed through, which should not be used.
            assert error.get_header('test') == 'test'

        # Should not raise a warning
        error.close()

    @pytest.mark.skipif(
        platform.python_implementation() == 'PyPy', reason='garbage collector works differently in pypy')
    def test_compat_httperror_autoclose(self):
        # Compat HTTPError should not autoclose response
        response = self.create_response(403)
        CompatHTTPError(HTTPError(response))
        assert not response.closed


if __name__ == '__main__':
    unittest.main()
