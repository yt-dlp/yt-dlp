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
    ExecAfterDownloadPP,
    FFmpegThumbnailsConvertorPP,
    MetadataFromFieldPP,
    MetadataFromTitlePP,
)


class TestMetadataFromField(unittest.TestCase):
    def test_format_to_regex(self):
        pp = MetadataFromFieldPP(None, ['title:%(title)s - %(artist)s'])
        self.assertEqual(pp._data[0]['regex'], r'(?P<title>.+)\ \-\ (?P<artist>.+)')

    def test_field_to_outtmpl(self):
        pp = MetadataFromFieldPP(None, ['title:%(title)s : %(artist)s'])
        self.assertEqual(pp._data[0]['tmpl'], '%(title)s')

    def test_in_out_seperation(self):
        pp = MetadataFromFieldPP(None, ['%(title)s \\: %(artist)s:%(title)s : %(artist)s'])
        self.assertEqual(pp._data[0]['in'], '%(title)s : %(artist)s')
        self.assertEqual(pp._data[0]['out'], '%(title)s : %(artist)s')


class TestMetadataFromTitle(unittest.TestCase):
    def test_format_to_regex(self):
        pp = MetadataFromTitlePP(None, '%(title)s - %(artist)s')
        self.assertEqual(pp._titleregex, r'(?P<title>.+)\ \-\ (?P<artist>.+)')


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


class TestExecAfterDownload(unittest.TestCase):
    def test_parse_cmd(self):
        pp = ExecAfterDownloadPP(YoutubeDL(), '')
        info = {'filepath': 'file name'}
        quoted_filepath = compat_shlex_quote(info['filepath'])

        self.assertEqual(pp.parse_cmd('echo', info), 'echo %s' % quoted_filepath)
        self.assertEqual(pp.parse_cmd('echo.{}', info), 'echo.%s' % quoted_filepath)
        self.assertEqual(pp.parse_cmd('echo "%(filepath)s"', info), 'echo "%s"' % info['filepath'])
