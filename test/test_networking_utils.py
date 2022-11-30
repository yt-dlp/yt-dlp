#!/usr/bin/env python3

# Allow direct execution
import io
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
        self.assertEqual(req.headers, CaseInsensitiveDict({'test': 'test'}))
        req.update(headers={'teSt2': 'test2'})
        self.assertEqual(req.headers, CaseInsensitiveDict({'test': 'test', 'test2': 'test2'}))

        req.headers = new_headers = CaseInsensitiveDict({'test': 'test'})
        self.assertEqual(req.headers, CaseInsensitiveDict({'test': 'test'}))
        self.assertIs(req.headers, new_headers)

        # test converts dict to case insensitive dict
        req.headers = new_headers = {'test2': 'test2'}
        self.assertIsInstance(req.headers, CaseInsensitiveDict)
        self.assertIsNot(req.headers, new_headers)

    def test_data_type(self):
        req = Request('http://example.com')
        # test bytes is allowed
        req.data = b'test'
        self.assertEqual(req.data, b'test')
        # test iterable of bytes is allowed
        i = [b'test', b'test2']
        req.data = i
        self.assertEqual(req.data, i)

        # test file-like object is allowed
        f = io.BytesIO(b'test')
        req.data = f
        self.assertEqual(req.data, f)

        # common mistake: test str not allowed
        with self.assertRaises(TypeError):
            req.data = 'test'
        self.assertNotEqual(req.data, 'test')

        # common mistake: test dict is not allowed
        with self.assertRaises(TypeError):
            req.data = {'test': 'test'}
        self.assertNotEqual(req.data, {'test': 'test'})

    def test_extract_basic_auth(self):
        auth_header = lambda url: Request(url).get_header('Authorization')
        self.assertFalse(auth_header('http://foo.bar'))
        self.assertFalse(auth_header('http://:foo.bar'))
        self.assertEqual(auth_header('http://@foo.bar'), 'Basic Og==')
        self.assertEqual(auth_header('http://:pass@foo.bar'), 'Basic OnBhc3M=')
        self.assertEqual(auth_header('http://user:@foo.bar'), 'Basic dXNlcjo=')
        self.assertEqual(auth_header('http://user:pass@foo.bar'), 'Basic dXNlcjpwYXNz')

    def test_handler_preference(self):
        req = Request('http://example.com')
        self.assertEqual(req.preferred_handlers, [])
        req = Request('http://example.com', preferred_handlers=['Urllib'])
        self.assertEqual(req.preferred_handlers, ['Urllib'])
        req.preferred_handlers.append('Test')
        self.assertEqual(req.preferred_handlers, ['Urllib', 'Test'])


if __name__ == '__main__':
    unittest.main()
