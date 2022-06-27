#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from yt_dlp.networking.utils import select_proxy
from yt_dlp.networking import Request
from yt_dlp.utils import CaseInsensitiveDict

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestNetworkingUtils(unittest.TestCase):

    def test_select_proxy(self):
        proxies = {
            'all': 'socks5://example.com',
            'http': 'http://example.com:1080',
        }

        self.assertEqual(select_proxy('https://example.com', proxies), proxies['all'])
        self.assertEqual(select_proxy('http://example.com', proxies), proxies['http'])


class TestRequest(unittest.TestCase):
    def test_method(self):
        req = Request('http://example.com')
        self.assertEqual(req.method, 'GET')
        req2 = req.copy()
        req2.data = b'test'
        self.assertEqual(req2.method, 'POST')
        self.assertEqual(req.method, 'GET')
        req2.data = None
        self.assertEqual(req2.method, 'GET')

    def test_headers(self):
        req = Request('http://example.com', headers={'tesT': 'test'})
        self.assertEqual(req.headers, {'test': 'test'})
        req.update(headers={'teSt2': 'test2'})
        self.assertEqual(req.headers, {'test': 'test', 'test2': 'test2'})

        req.headers = new_headers = CaseInsensitiveDict({'test': 'test'})
        self.assertEqual(req.headers, {'test': 'test'})
        self.assertIs(req.headers, new_headers)

        req.headers = new_headers = {'test2': 'test2'}
        self.assertEqual(req.headers, {'test2': 'test2'})
        self.assertIsNot(req.headers, new_headers)

if __name__ == '__main__':
    unittest.main()
