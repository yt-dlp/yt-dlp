#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import struct

from yt_dlp import compat
from yt_dlp.compat import urllib  # isort: split
from yt_dlp.compat import compat_etree_fromstring, compat_expanduser
from yt_dlp.compat.urllib.request import getproxies


class TestCompat(unittest.TestCase):
    def test_compat_passthrough(self):
        with self.assertWarns(DeprecationWarning):
            _ = compat.compat_basestring

        with self.assertWarns(DeprecationWarning):
            _ = compat.WINDOWS_VT_MODE

        self.assertEqual(urllib.request.getproxies, getproxies)

        with self.assertWarns(DeprecationWarning):
            _ = compat.compat_pycrypto_AES  # Must not raise error

    def test_compat_expanduser(self):
        old_home = os.environ.get('HOME')
        test_str = R'C:\Documents and Settings\тест\Application Data'
        try:
            os.environ['HOME'] = test_str
            self.assertEqual(compat_expanduser('~'), test_str)
        finally:
            os.environ['HOME'] = old_home or ''

    def test_compat_etree_fromstring(self):
        xml = '''
            <root foo="bar" spam="中文">
                <normal>foo</normal>
                <chinese>中文</chinese>
                <foo><bar>spam</bar></foo>
            </root>
        '''
        doc = compat_etree_fromstring(xml.encode())
        self.assertTrue(isinstance(doc.attrib['foo'], str))
        self.assertTrue(isinstance(doc.attrib['spam'], str))
        self.assertTrue(isinstance(doc.find('normal').text, str))
        self.assertTrue(isinstance(doc.find('chinese').text, str))
        self.assertTrue(isinstance(doc.find('foo/bar').text, str))

    def test_compat_etree_fromstring_doctype(self):
        xml = '''<?xml version="1.0"?>
<!DOCTYPE smil PUBLIC "-//W3C//DTD SMIL 2.0//EN" "http://www.w3.org/2001/SMIL20/SMIL20.dtd">
<smil xmlns="http://www.w3.org/2001/SMIL20/Language"></smil>'''
        compat_etree_fromstring(xml)

    def test_struct_unpack(self):
        self.assertEqual(struct.unpack('!B', b'\x00'), (0,))


if __name__ == '__main__':
    unittest.main()
