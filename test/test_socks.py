#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import random
import subprocess

from test.helper import get_params, is_download_test
from test.test_networking import with_make_rh
from yt_dlp.networking import Request


@is_download_test
class TestMultipleSocks(unittest.TestCase):
    @staticmethod
    def _check_params(attrs):
        params = get_params()
        for attr in attrs:
            if attr not in params:
                print('Missing %s. Skipping.' % attr)
                return
        return params

    @with_make_rh()
    def test_proxy_http(self, make_rh):
        params = self._check_params(['primary_proxy', 'primary_server_ip'])
        if params is None:
            return
        with make_rh({'proxy': params['primary_proxy']}) as rh:
            self.assertEqual(
                rh.handle(Request('http://yt-dl.org/ip')).read().decode('utf-8'),
                params['primary_server_ip'])

    @with_make_rh()
    def test_proxy_https(self, make_rh):
        params = self._check_params(['primary_proxy', 'primary_server_ip'])
        if params is None:
            return
        with make_rh({'proxy': params['primary_proxy']}) as rh:
            self.assertEqual(
                rh.handle(Request('https://yt-dl.org/ip')).read().decode('utf-8'),
                params['primary_server_ip'])

    @with_make_rh()
    def test_secondary_proxy_http(self, make_rh):
        params = self._check_params(['secondary_proxy', 'secondary_server_ip'])
        if params is None:
            return
        with make_rh() as rh:
            req = Request('http://yt-dl.org/ip', proxies={'all': params['secondary_proxy']})
            self.assertEqual(
                rh.handle(req).read().decode('utf-8'),
                params['secondary_server_ip'])

    @with_make_rh()
    def test_secondary_proxy_https(self, make_rh):
        params = self._check_params(['secondary_proxy', 'secondary_server_ip'])
        if params is None:
            return
        with make_rh() as rh:
            req = Request('http://yt-dl.org/ip', proxies={'all': params['secondary_proxy']})
            self.assertEqual(
                rh.handle(req).read().decode('utf-8'),
                params['secondary_server_ip'])


@is_download_test
class TestSocks(unittest.TestCase):
    _SKIP_SOCKS_TEST = True

    def setUp(self):
        if self._SKIP_SOCKS_TEST:
            return

        self.port = random.randint(20000, 30000)
        self.server_process = subprocess.Popen([
            'srelay', '-f', '-i', '127.0.0.1:%d' % self.port],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def tearDown(self):
        if self._SKIP_SOCKS_TEST:
            return

        self.server_process.terminate()
        self.server_process.communicate()

    @with_make_rh()
    def _get_ip(self, make_rh, protocol):
        if self._SKIP_SOCKS_TEST:
            return '127.0.0.1'

        with make_rh({
            'proxy': '%s://127.0.0.1:%d' % (protocol, self.port),
        }) as rh:
            return rh.handle(Request('http://yt-dl.org/ip')).read().decode('utf-8')

    def test_socks4(self):
        self.assertTrue(isinstance(self._get_ip('socks4'), str))

    def test_socks4a(self):
        self.assertTrue(isinstance(self._get_ip('socks4a'), str))

    def test_socks5(self):
        self.assertTrue(isinstance(self._get_ip('socks5'), str))


if __name__ == '__main__':
    unittest.main()
