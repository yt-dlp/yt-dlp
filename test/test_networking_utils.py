#!/usr/bin/env python3

# Allow direct execution
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contextlib
import io
import platform
import random
import ssl
import urllib.error
import warnings

from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.dependencies import certifi
from yt_dlp.networking import Response
from yt_dlp.networking._helper import (
    InstanceStoreMixin,
    add_accept_encoding_header,
    get_redirect_method,
    make_socks_proxy_opts,
    select_proxy,
    ssl_load_certs,
)
from yt_dlp.networking.exceptions import (
    HTTPError,
    IncompleteRead,
    _CompatHTTPError,
)
from yt_dlp.socks import ProxyType
from yt_dlp.utils.networking import HTTPHeaderDict

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

    @pytest.mark.skipif(not certifi, reason='certifi is not installed')
    def test_load_certifi(self):
        context_certifi = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context_certifi.load_verify_locations(cafile=certifi.where())
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_load_certs(context, use_certifi=True)
        assert context.get_ca_certs() == context_certifi.get_ca_certs()

        context_default = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context_default.load_default_certs()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_load_certs(context, use_certifi=False)
        assert context.get_ca_certs() == context_default.get_ca_certs()

        if context_default.get_ca_certs() == context_certifi.get_ca_certs():
            pytest.skip('System uses certifi as default. The test is not valid')

    @pytest.mark.parametrize('method,status,expected', [
        ('GET', 303, 'GET'),
        ('HEAD', 303, 'HEAD'),
        ('PUT', 303, 'GET'),
        ('POST', 301, 'GET'),
        ('HEAD', 301, 'HEAD'),
        ('POST', 302, 'GET'),
        ('HEAD', 302, 'HEAD'),
        ('PUT', 302, 'PUT'),
        ('POST', 308, 'POST'),
        ('POST', 307, 'POST'),
        ('HEAD', 308, 'HEAD'),
        ('HEAD', 307, 'HEAD'),
    ])
    def test_get_redirect_method(self, method, status, expected):
        assert get_redirect_method(method, status) == expected

    @pytest.mark.parametrize('headers,supported_encodings,expected', [
        ({'Accept-Encoding': 'br'}, ['gzip', 'br'], {'Accept-Encoding': 'br'}),
        ({}, ['gzip', 'br'], {'Accept-Encoding': 'gzip, br'}),
        ({'Content-type': 'application/json'}, [], {'Content-type': 'application/json', 'Accept-Encoding': 'identity'}),
    ])
    def test_add_accept_encoding_header(self, headers, supported_encodings, expected):
        headers = HTTPHeaderDict(headers)
        add_accept_encoding_header(headers, supported_encodings)
        assert headers == HTTPHeaderDict(expected)


class TestInstanceStoreMixin:

    class FakeInstanceStoreMixin(InstanceStoreMixin):
        def _create_instance(self, **kwargs):
            return random.randint(0, 1000000)

        def _close_instance(self, instance):
            pass

    def test_mixin(self):
        mixin = self.FakeInstanceStoreMixin()
        assert mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}}) == mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}})

        assert mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'e', 4}}) != mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}})

        assert mixin._get_instance(d={'a': 1, 'b': 2, 'c': {'d', 4}} != mixin._get_instance(d={'a': 1, 'b': 2, 'g': {'d', 4}}))

        assert mixin._get_instance(d={'a': 1}, e=[1, 2, 3]) == mixin._get_instance(d={'a': 1}, e=[1, 2, 3])

        assert mixin._get_instance(d={'a': 1}, e=[1, 2, 3]) != mixin._get_instance(d={'a': 1}, e=[1, 2, 3, 4])

        cookiejar = YoutubeDLCookieJar()
        assert mixin._get_instance(b=[1, 2], c=cookiejar) == mixin._get_instance(b=[1, 2], c=cookiejar)

        assert mixin._get_instance(b=[1, 2], c=cookiejar) != mixin._get_instance(b=[1, 2], c=YoutubeDLCookieJar())

        # Different order
        assert mixin._get_instance(c=cookiejar, b=[1, 2]) == mixin._get_instance(b=[1, 2], c=cookiejar)

        m = mixin._get_instance(t=1234)
        assert mixin._get_instance(t=1234) == m
        mixin._clear_instances()
        assert mixin._get_instance(t=1234) != m


class TestNetworkingExceptions:

    @staticmethod
    def create_response(status):
        return Response(fp=io.BytesIO(b'test'), url='http://example.com', headers={'tesT': 'test'}, status=status)

    @pytest.mark.parametrize('http_error_class', [HTTPError, lambda r: _CompatHTTPError(HTTPError(r))])
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

    @pytest.mark.parametrize('http_error_class', [HTTPError, lambda *args, **kwargs: _CompatHTTPError(HTTPError(*args, **kwargs))])
    def test_redirect_http_error(self, http_error_class):
        response = self.create_response(301)
        error = http_error_class(response, redirect_loop=True)
        assert str(error) == error.msg == 'HTTP Error 301: Moved Permanently (redirect loop detected)'
        assert error.reason == 'Moved Permanently'

    def test_compat_http_error(self):
        response = self.create_response(403)
        error = _CompatHTTPError(HTTPError(response))
        assert isinstance(error, HTTPError)
        assert isinstance(error, urllib.error.HTTPError)

        @contextlib.contextmanager
        def raises_deprecation_warning():
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
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
    def test_compat_http_error_autoclose(self):
        # Compat HTTPError should not autoclose response
        response = self.create_response(403)
        _CompatHTTPError(HTTPError(response))
        assert not response.closed

    def test_incomplete_read_error(self):
        error = IncompleteRead(4, 3, cause='test')
        assert isinstance(error, IncompleteRead)
        assert repr(error) == '<IncompleteRead: 4 bytes read, 3 more expected>'
        assert str(error) == error.msg == '4 bytes read, 3 more expected'
        assert error.partial == 4
        assert error.expected == 3
        assert error.cause == 'test'

        error = IncompleteRead(3)
        assert repr(error) == '<IncompleteRead: 3 bytes read>'
        assert str(error) == '3 bytes read'
