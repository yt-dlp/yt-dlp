#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import unittest

from yt_dlp import webvtt


class TestWebVTT(unittest.TestCase):
    def test_parse_negative_mpegts_timestamp_map(self):
        blocks = list(webvtt.parse_fragment(b'''WEBVTT
X-TIMESTAMP-MAP=MPEGTS:-6000,LOCAL:00:00:00.000

00:00:03.770 --> 00:00:05.000
Text
'''))

        self.assertIsInstance(blocks[0], webvtt.Magic)
        self.assertEqual(blocks[0].mpegts, -6000)
        self.assertEqual(blocks[0].local, 0)


if __name__ == '__main__':
    unittest.main()
