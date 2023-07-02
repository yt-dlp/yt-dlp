#!/usr/bin/env python3

# Allow direct execution
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

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


if __name__ == '__main__':
    unittest.main()
