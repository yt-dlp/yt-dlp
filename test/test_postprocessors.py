#!/usr/bin/env python3

from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_shlex_quote
from yt_dlp.postprocessor import (
    ExecPP,
    FFmpegThumbnailsConvertorPP,
    MetadataFromFieldPP,
    MetadataParserPP,
)


class TestMetadataFromField(unittest.TestCase):

    def test_format_to_regex(self):
        self.assertEqual(
            MetadataParserPP.format_to_regex('%(title)s - %(artist)s'),
            r'(?P<title>.+)\ \-\ (?P<artist>.+)')
        self.assertEqual(MetadataParserPP.format_to_regex(r'(?P<x>.+)'), r'(?P<x>.+)')

    def test_field_to_template(self):
        self.assertEqual(MetadataParserPP.field_to_template('title'), '%(title)s')
        self.assertEqual(MetadataParserPP.field_to_template('1'), '1')
        self.assertEqual(MetadataParserPP.field_to_template('foo bar'), 'foo bar')
        self.assertEqual(MetadataParserPP.field_to_template(' literal'), ' literal')

    def test_metadatafromfield(self):
        self.assertEqual(
            MetadataFromFieldPP.to_action('%(title)s \\: %(artist)s:%(title)s : %(artist)s'),
            (MetadataParserPP.Actions.INTERPRET, '%(title)s : %(artist)s', '%(title)s : %(artist)s'))


class TestConvertThumbnail(unittest.TestCase):
    def test_escaping(self):
        pp = FFmpegThumbnailsConvertorPP()
        if not pp.available:
            print('Skipping: ffmpeg not found')
            return

        file = 'test/testdata/thumbnails/foo %d bar/foo_%d.{}'
        tests = (('webp', 'png'), ('png', 'jpg'))

        for inp, out in tests:
            out_file = file.format(out)
            if os.path.exists(out_file):
                os.remove(out_file)
            pp.convert_thumbnail(file.format(inp), out)
            assert os.path.exists(out_file)

        for _, out in tests:
            os.remove(file.format(out))


class TestExec(unittest.TestCase):
    def test_parse_cmd(self):
        pp = ExecPP(YoutubeDL(), '')
        info = {'filepath': 'file name'}
        cmd = 'echo %s' % compat_shlex_quote(info['filepath'])

        self.assertEqual(pp.parse_cmd('echo', info), cmd)
        self.assertEqual(pp.parse_cmd('echo {}', info), cmd)
        self.assertEqual(pp.parse_cmd('echo %(filepath)q', info), cmd)
