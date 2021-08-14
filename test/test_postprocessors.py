#!/usr/bin/env python3

from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re

from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_shlex_quote
from yt_dlp.postprocessor import (
    ExecPP,
    FFmpegThumbnailsConvertorPP,
    MetadataFromFieldPP,
    MetadataParserPP,
    FFmpegRemoveChaptersPP,
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


class TestRemoveChaptersPP(unittest.TestCase):
    def test_concat_spec(self):
        def test(*ranges_to_cut, expected, duration=30):
            opts = FFmpegRemoveChaptersPP._make_concat_opts(ranges_to_cut, duration)
            self.assertEqual(
                ''.join(FFmpegRemoveChaptersPP._concat_spec(['test'] * len(opts), opts)),
                "\nfile 'file:test'\n".join(['ffconcat version 1.0'] + expected) + '\n')

        test((1, 2), (10, 20), expected=[
            'outpoint 1.000000',
            'inpoint 2.000000\noutpoint 10.000000',
            'inpoint 20.000000'])
        test((0, 1), (10, 20), expected=[
            'inpoint 1.000000\noutpoint 10.000000',
            'inpoint 20.000000'])
        test((1, 2), (10, 30), expected=[
            'outpoint 1.000000',
            'inpoint 2.000000\noutpoint 10.000000'])

    def test_quote_for_concat(self):
        self.assertEqual(
            FFmpegRemoveChaptersPP._quote_for_concat("special ' ''characters'''galore"),
            r"'special '\'' '\'\''characters'\'\'\''galore'")
        self.assertEqual(
            FFmpegRemoveChaptersPP._quote_for_concat("'''special ' characters ' galore"),
            r"\'\'\''special '\'' characters '\'' galore'")
        self.assertEqual(
            FFmpegRemoveChaptersPP._quote_for_concat("special ' characters ' galore'''"),
            r"'special '\'' characters '\'' galore'\'\'\'")

    def test_remove_chapters_from_infodict(self):

        timestamps = [
            {('normal 0', 0, 1), ('normal 1', 1, 4), ('normal 2', 4, 6), ('normal 3', 7, 8)},
            {('inside', 2, 3), ('c', 2, 5), ('overlap', 5, 7), ('overlap2', 5, 7)},
        ]

        def set_to_chapters(chapters):
            return [{'title': title, 'start_time': start, 'end_time': end}
                    for title, start, end in chapters]

        def set_from_chapters(chapters):
            return set((c['title'], c['start_time'], c['end_time']) for c in chapters)

        def test(regex, expected, remaining_list):
            regex = re.compile(regex)
            chapters_list = list(map(set_to_chapters, timestamps))

            removed = FFmpegRemoveChaptersPP._remove_chapters_from_infodict(*chapters_list, regexes=[regex])
            self.assertEqual(list(map(tuple, removed)), expected)
            for chapters, remaining in zip(chapters_list, remaining_list):
                self.assertEqual([set_from_chapters(chapters) for chapters in chapters_list], remaining_list)

            # Test with all chapter lists combined
            chapters = [c for chapters in timestamps for c in set_to_chapters(chapters)]
            removed = FFmpegRemoveChaptersPP._remove_chapters_from_infodict(chapters, regexes=[regex])
            self.assertEqual(list(map(tuple, removed)), expected)
            self.assertEqual(set_from_chapters(chapters), set.union(*remaining_list))

        # Remove nothing
        test('none', [], [
             {('normal 0', 0, 1), ('normal 1', 1, 4), ('normal 2', 4, 6), ('normal 3', 7, 8)},
             {('inside', 2, 3), ('overlap', 5, 7), ('overlap2', 5, 7), ('c', 2, 5)}])

        # Remove independent chapters
        test('normal 0', [(0, 1)], [
             {('normal 1', 0, 3), ('normal 2', 3, 5), ('normal 3', 6, 7)},
             {('inside', 1, 2), ('overlap', 4, 6), ('overlap2', 4, 6), ('c', 1, 4)}])
        test('normal 0|normal 3', [(0, 1), (7, 8)], [
             {('normal 1', 0, 3), ('normal 2', 3, 5)},
             {('inside', 1, 2), ('overlap', 4, 6), ('overlap2', 4, 6), ('c', 1, 4)}])

        # Remove a chapter that is identical to another chapter
        test('overlap2', [(5, 7)], [
             {('normal 0', 0, 1), ('normal 1', 1, 4), ('normal 2', 4, 5), ('normal 3', 5, 6)},
             {('inside', 2, 3), ('c', 2, 5)}])

        # Remove a chapter that overlaps another chapter
        test('overlap', [(5, 7)], [
             {('normal 0', 0, 1), ('normal 1', 1, 4), ('normal 2', 4, 5), ('normal 3', 5, 6)},
             {('inside', 2, 3), ('c', 2, 5)}])

        # Remove a chapter from inside another chapter
        test('inside', [(2, 3)], [
             {('normal 0', 0, 1), ('normal 1', 1, 3), ('normal 2', 3, 5), ('normal 3', 6, 7)},
             {('overlap', 4, 6), ('overlap2', 4, 6), ('c', 2, 4)}])

        # Remove a chapter enclosing another chapter
        test('normal 1', [(1, 4)], [
             {('normal 0', 0, 1), ('normal 2', 1, 3), ('normal 3', 4, 5)},
             {('overlap', 2, 4), ('overlap2', 2, 4), ('c', 1, 2)}])

        # Remove 2 chapters that touch each other
        test('normal 0|normal 1', [(0, 4)], [
             {('normal 2', 0, 2), ('normal 3', 3, 4)},
             {('overlap', 1, 3), ('overlap2', 1, 3), ('c', 0, 1)}])

        # Remove 2 overlapping chapters
        test('overlap|normal 2', [(4, 7)], [
             {('normal 0', 0, 1), ('normal 1', 1, 4), ('normal 3', 4, 5)},
             {('inside', 2, 3), ('c', 2, 4)}])

        # Remove 2 chapters, one inside the other
        test('normal 1|inside', [(1, 4)], [
             {('normal 0', 0, 1), ('normal 2', 1, 3), ('normal 3', 4, 5)},
             {('overlap', 2, 4), ('overlap2', 2, 4), ('c', 1, 2)}])

        # Remove 2 chapters that together enclose another chapter
        test('normal 1|normal 2', [(1, 6)], [
             {('normal 0', 0, 1), ('normal 3', 2, 3)},
             {('overlap', 1, 2), ('overlap2', 1, 2)}])

        # Remove 2 chapters with same start
        test('inside|c', [(2, 5)], [
             {('normal 0', 0, 1), ('normal 1', 1, 2), ('normal 2', 2, 3), ('normal 3', 4, 5)},
             {('overlap', 2, 4), ('overlap2', 2, 4)}])
