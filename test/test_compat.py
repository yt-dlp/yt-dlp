#!/usr/bin/env python3

# Allow direct execution
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import struct

from yt_dlp import compat
from yt_dlp.compat import urllib  # isort: split
from yt_dlp.compat import compat_expanduser, compat_datetime_from_timestamp
from yt_dlp.compat.urllib.request import getproxies


class TestCompat(unittest.TestCase):
    def test_compat_passthrough(self):
        with self.assertWarns(DeprecationWarning):
            _ = compat.compat_basestring

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

    def test_struct_unpack(self):
        self.assertEqual(struct.unpack('!B', b'\x00'), (0,))

    def test_compat_datetime_from_timestamp(self):
        self.assertEqual(
            compat_datetime_from_timestamp(0),
            dt.datetime(1970, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(
            compat_datetime_from_timestamp(1),
            dt.datetime(1970, 1, 1, 0, 0, 1, tzinfo=dt.timezone.utc))
        self.assertEqual(
            compat_datetime_from_timestamp(3600),
            dt.datetime(1970, 1, 1, 1, 0, 0, tzinfo=dt.timezone.utc))

        self.assertEqual(
            compat_datetime_from_timestamp(-1),
            dt.datetime(1969, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc))
        self.assertEqual(
            compat_datetime_from_timestamp(-86400),
            dt.datetime(1969, 12, 31, 0, 0, 0, tzinfo=dt.timezone.utc))

        self.assertEqual(
            compat_datetime_from_timestamp(0.5),
            dt.datetime(1970, 1, 1, 0, 0, 0, 500000, tzinfo=dt.timezone.utc))
        self.assertEqual(
            compat_datetime_from_timestamp(1.000001),
            dt.datetime(1970, 1, 1, 0, 0, 1, 1, tzinfo=dt.timezone.utc))
        self.assertEqual(
            compat_datetime_from_timestamp(-1.25),
            dt.datetime(1969, 12, 31, 23, 59, 58, 750000, tzinfo=dt.timezone.utc))

        self.assertEqual(
            compat_datetime_from_timestamp(-1577923200),
            dt.datetime(1920, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(
            compat_datetime_from_timestamp(4102444800),
            dt.datetime(2100, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc))

        self.assertEqual(
            compat_datetime_from_timestamp(173568960000),
            dt.datetime(7470, 3, 8, 0, 0, 0, tzinfo=dt.timezone.utc))


if __name__ == '__main__':
    unittest.main()
