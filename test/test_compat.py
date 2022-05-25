#!/usr/bin/env python3
# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from yt_dlp import compat
from yt_dlp.compat import (
    compat_etree_fromstring,
    compat_expanduser,
    compat_getenv,
    compat_setenv,
    compat_str,
    compat_struct_unpack,
    compat_urllib_parse_unquote,
    compat_urllib_parse_unquote_plus,
    compat_urllib_parse_urlencode,
)


class TestCompat(unittest.TestCase):
    def test_compat_passthrough(self):
        with self.assertWarns(DeprecationWarning):
            compat.compat_basestring

        compat.asyncio.events  # Must not raise error

    def test_compat_getenv(self):
        test_str = 'тест'
        compat_setenv('yt_dlp_COMPAT_GETENV', test_str)
        self.assertEqual(compat_getenv('yt_dlp_COMPAT_GETENV'), test_str)

    def test_compat_setenv(self):
        test_var = 'yt_dlp_COMPAT_SETENV'
        test_str = 'тест'
        compat_setenv(test_var, test_str)
        compat_getenv(test_var)
        self.assertEqual(compat_getenv(test_var), test_str)

    def test_compat_expanduser(self):
        old_home = os.environ.get('HOME')
        test_str = R'C:\Documents and Settings\тест\Application Data'
        try:
            compat_setenv('HOME', test_str)
            self.assertEqual(compat_expanduser('~'), test_str)
        finally:
            compat_setenv('HOME', old_home or '')

    def test_compat_urllib_parse_unquote(self):
        self.assertEqual(compat_urllib_parse_unquote('abc%20def'), 'abc def')
        self.assertEqual(compat_urllib_parse_unquote('%7e/abc+def'), '~/abc+def')
        self.assertEqual(compat_urllib_parse_unquote(''), '')
        self.assertEqual(compat_urllib_parse_unquote('%'), '%')
        self.assertEqual(compat_urllib_parse_unquote('%%'), '%%')
        self.assertEqual(compat_urllib_parse_unquote('%%%'), '%%%')
        self.assertEqual(compat_urllib_parse_unquote('%2F'), '/')
        self.assertEqual(compat_urllib_parse_unquote('%2f'), '/')
        self.assertEqual(compat_urllib_parse_unquote('%E6%B4%A5%E6%B3%A2'), '津波')
        self.assertEqual(
            compat_urllib_parse_unquote('''<meta property="og:description" content="%E2%96%81%E2%96%82%E2%96%83%E2%96%84%25%E2%96%85%E2%96%86%E2%96%87%E2%96%88" />
%<a href="https://ar.wikipedia.org/wiki/%D8%AA%D8%B3%D9%88%D9%86%D8%A7%D9%85%D9%8A">%a'''),
            '''<meta property="og:description" content="▁▂▃▄%▅▆▇█" />
%<a href="https://ar.wikipedia.org/wiki/تسونامي">%a''')
        self.assertEqual(
            compat_urllib_parse_unquote('''%28%5E%E2%97%A3_%E2%97%A2%5E%29%E3%81%A3%EF%B8%BB%E3%83%87%E2%95%90%E4%B8%80    %E2%87%80    %E2%87%80    %E2%87%80    %E2%87%80    %E2%87%80    %E2%86%B6%I%Break%25Things%'''),
            '''(^◣_◢^)っ︻デ═一    ⇀    ⇀    ⇀    ⇀    ⇀    ↶%I%Break%Things%''')

    def test_compat_urllib_parse_unquote_plus(self):
        self.assertEqual(compat_urllib_parse_unquote_plus('abc%20def'), 'abc def')
        self.assertEqual(compat_urllib_parse_unquote_plus('%7e/abc+def'), '~/abc def')

    def test_compat_urllib_parse_urlencode(self):
        self.assertEqual(compat_urllib_parse_urlencode({'abc': 'def'}), 'abc=def')
        self.assertEqual(compat_urllib_parse_urlencode({'abc': b'def'}), 'abc=def')
        self.assertEqual(compat_urllib_parse_urlencode({b'abc': 'def'}), 'abc=def')
        self.assertEqual(compat_urllib_parse_urlencode({b'abc': b'def'}), 'abc=def')
        self.assertEqual(compat_urllib_parse_urlencode([('abc', 'def')]), 'abc=def')
        self.assertEqual(compat_urllib_parse_urlencode([('abc', b'def')]), 'abc=def')
        self.assertEqual(compat_urllib_parse_urlencode([(b'abc', 'def')]), 'abc=def')
        self.assertEqual(compat_urllib_parse_urlencode([(b'abc', b'def')]), 'abc=def')

    def test_compat_etree_fromstring(self):
        xml = '''
            <root foo="bar" spam="中文">
                <normal>foo</normal>
                <chinese>中文</chinese>
                <foo><bar>spam</bar></foo>
            </root>
        '''
        doc = compat_etree_fromstring(xml.encode())
        self.assertTrue(isinstance(doc.attrib['foo'], compat_str))
        self.assertTrue(isinstance(doc.attrib['spam'], compat_str))
        self.assertTrue(isinstance(doc.find('normal').text, compat_str))
        self.assertTrue(isinstance(doc.find('chinese').text, compat_str))
        self.assertTrue(isinstance(doc.find('foo/bar').text, compat_str))

    def test_compat_etree_fromstring_doctype(self):
        xml = '''<?xml version="1.0"?>
<!DOCTYPE smil PUBLIC "-//W3C//DTD SMIL 2.0//EN" "http://www.w3.org/2001/SMIL20/SMIL20.dtd">
<smil xmlns="http://www.w3.org/2001/SMIL20/Language"></smil>'''
        compat_etree_fromstring(xml)

    def test_struct_unpack(self):
        self.assertEqual(compat_struct_unpack('!B', b'\x00'), (0,))


if __name__ == '__main__':
    unittest.main()
