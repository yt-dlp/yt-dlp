#!/usr/bin/env python

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io

from yt_dlp.postprocessor.mp4direct import (
    parse_mp4_boxes,
    write_mp4_boxes,
)

TEST_SEQUENCE = [
    ('test', b'123456'),
    ('trak', b''),
    ('helo', b'abcdef'),
    ('1984', b'1q84'),
    ('moov', b''),
    ('keys', b'2022'),
    (None, 'moov'),
    ('topp', b'1991'),
    (None, 'trak'),
]

# on-file reprensetation of the above sequence
TEST_BYTES = b'\x00\x00\x00\x0etest123456\x00\x00\x00Btrak\x00\x00\x00\x0eheloabcdef\x00\x00\x00\x0c19841q84\x00\x00\x00\x14moov\x00\x00\x00\x0ckeys2022\x00\x00\x00\x0ctopp1991'


class TestMP4Parser(unittest.TestCase):
    def test_write_sequence(self):
        with io.BytesIO() as w:
            write_mp4_boxes(w, TEST_SEQUENCE)
            bs = w.getvalue()
        self.assertEqual(TEST_BYTES, bs)

    def test_read_bytes(self):
        with io.BytesIO(TEST_BYTES) as r:
            result = list(parse_mp4_boxes(r))
        self.assertListEqual(TEST_SEQUENCE, result)

    def test_mismatched_box_end(self):
        with io.BytesIO() as w, self.assertRaises(AssertionError):
            write_mp4_boxes(w, [
                ('moov', b''),
                ('trak', b''),
                (None, 'moov'),
                (None, 'trak'),
            ])
