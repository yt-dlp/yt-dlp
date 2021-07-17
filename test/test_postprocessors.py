#!/usr/bin/env python3

from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
from typing import Optional, Sequence, List, MutableSequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_shlex_quote
from yt_dlp.postprocessor import (
    ExecPP,
    FFmpegThumbnailsConvertorPP,
    MetadataFromFieldPP,
    MetadataParserPP,
    ModifyChaptersPP
)
from yt_dlp.postprocessor.modify_chapters import Chapter


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


class TestModifyChaptersPP(unittest.TestCase):
    def setUp(self):
        self._pp = ModifyChaptersPP(None)

    @staticmethod
    def _sponsor_chapter(start: float, end: float, cat: str, remove=False) -> Chapter:
        c = {'start_time': start, 'end_time': end, 'categories': [(cat, start, end)]}
        if remove:
            c['remove'] = True
        return c

    @staticmethod
    def _chapter(start: float, end: float, title: Optional[str] = None, remove=False) -> Chapter:
        c = {'start_time': start, 'end_time': end}
        if title is not None:
            c['title'] = title
        if remove:
            c['remove'] = True
        return c

    def _chapters(self, ends: Sequence[float], titles: Sequence[str]) -> List[Chapter]:
        self.assertEqual(len(ends), len(titles))
        start = 0
        chapters: List[Chapter] = []
        for e, t in zip(ends, titles):
            chapters.append(self._chapter(start, e, t))
            start = e
        return chapters

    def _remove_marked_arrange_sponsors_test_impl(
            self, chapters: MutableSequence[Chapter], expected_chapters: Sequence[Chapter],
            expected_removed: Sequence[Chapter], expected_has_sponsors: bool):
        actual_chapters, actual_removed, actual_has_sponsors = (
            self._pp._remove_marked_arrange_sponsors(chapters))
        # Title and categories are meaningless if a cut is a merge of
        # multiple ordinary and sponsor chapters.
        for c in actual_removed:
            c.pop('title', None)
            c.pop('categories', None)
        self.assertSequenceEqual(expected_chapters, actual_chapters)
        self.assertSequenceEqual(expected_removed, actual_removed)
        self.assertEqual(expected_has_sponsors, actual_has_sponsors)

    def test_remove_marked_arrange_sponsors_CanGetThroughUnaltered(self):
        chapters = self._chapters([1, 2, 3, 4], ['c1', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, chapters, [], False)

    def test_remove_marked_arrange_sponsors_ChapterWithSponsors(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 2, 'sponsor'),
            self._sponsor_chapter(3, 4, 'preview'),
            self._sponsor_chapter(5, 6, 'sponsor')]
        expected = self._chapters(
            [1, 2, 3, 4, 5, 6, 7],
            ['c - 1', '[SponsorBlock]: Sponsor - 1', 'c - 2', '[SponsorBlock]: Preview/Recap',
             'c - 3', '[SponsorBlock]: Sponsor - 2', 'c - 4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_UniqueNamesForOverlappingSponsors(self):
        chapters = self._chapters([12], ['c']) + [
            self._sponsor_chapter(1, 3, 'sponsor'), self._sponsor_chapter(2, 4, 'selfpromo'),
            self._sponsor_chapter(5, 7, 'sponsor'), self._sponsor_chapter(6, 8, 'selfpromo'),
            self._sponsor_chapter(9, 11, 'selfpromo'), self._sponsor_chapter(10, 12, 'sponsor')]
        expected = self._chapters(
            [1, 4, 5, 8, 9, 12],
            ['c - 1', '[SponsorBlock]: Sponsor/Self-Promotion - 1',
             'c - 2', '[SponsorBlock]: Sponsor/Self-Promotion - 2',
             'c - 3', '[SponsorBlock]: Self-Promotion/Sponsor'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_ChapterWithCuts(self):
        cuts = [self._chapter(1, 2, remove=True),
                self._sponsor_chapter(3, 4, 'sponsor', remove=True),
                self._chapter(5, 6, remove=True)]
        chapters = self._chapters([7], ['c']) + cuts
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([4], ['c']), cuts, False)

    def test_remove_marked_arrange_sponsors_ChapterWithSponsorsAndCuts(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 2, 'sponsor'),
            self._sponsor_chapter(3, 4, 'selfpromo', remove=True),
            self._sponsor_chapter(5, 6, 'interaction')]
        expected = self._chapters([1, 2, 4, 5, 6],
                                  ['c - 1', '[SponsorBlock]: Sponsor', 'c - 2',
                                   '[SponsorBlock]: Interaction Reminder', 'c - 3'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(3, 4, remove=True)], True)

    def test_remove_marked_arrange_sponsors_ChapterWithSponsorCutInTheMiddle(self):
        cuts = [self._sponsor_chapter(2, 3, 'selfpromo', remove=True),
                self._chapter(4, 5, remove=True)]
        chapters = self._chapters([7], ['c']) + [self._sponsor_chapter(1, 6, 'sponsor')] + cuts
        expected = self._chapters(
            [1, 4, 5], ['c - 1', '[SponsorBlock]: Sponsor', 'c - 2'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, True)

    def test_remove_marked_arrange_sponsors_ChapterWithCutHidingSponsor(self):
        cuts = [self._sponsor_chapter(2, 5, 'selpromo', remove=True)]
        chapters = self._chapters([6], ['c']) + [
            self._sponsor_chapter(1, 2, 'intro'),
            self._sponsor_chapter(3, 4, 'sponsor'),
            self._sponsor_chapter(5, 6, 'outro'),
        ] + cuts
        expected = self._chapters(
            [1, 2, 3], ['c', '[SponsorBlock]: Intro', '[SponsorBlock]: Outro'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, True)

    def test_remove_marked_arrange_sponsors_ChapterWithAdjacentSponsors(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 2, 'sponsor'),
            self._sponsor_chapter(2, 3, 'selfpromo'),
            self._sponsor_chapter(3, 4, 'interaction')]
        expected = self._chapters(
            [1, 2, 3, 4, 7],
            ['c - 1', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Self-Promotion',
             '[SponsorBlock]: Interaction Reminder', 'c - 2'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_ChapterWithAdjacentCuts(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 2, 'sponsor'),
            self._sponsor_chapter(2, 3, 'interaction', remove=True),
            self._chapter(3, 4, remove=True),
            self._sponsor_chapter(4, 5, 'selpromo', remove=True),
            self._sponsor_chapter(5, 6, 'interaction')]
        expected = self._chapters([1, 2, 3, 4],
                                  ['c - 1', '[SponsorBlock]: Sponsor',
                                   '[SponsorBlock]: Interaction Reminder', 'c - 2'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(2, 5, remove=True)], True)

    def test_remove_marked_arrange_sponsors_ChapterWithOverlappingSponsors(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 3, 'sponsor'),
            self._sponsor_chapter(2, 5, 'selfpromo'),
            self._sponsor_chapter(4, 6, 'interaction')]
        expected = self._chapters(
            [1, 6, 7],
            ['c - 1', '[SponsorBlock]: Sponsor/Self-Promotion/Interaction Reminder', 'c - 2'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_ChapterWithOverlappingCuts(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 3, 'sponsor', remove=True),
            self._sponsor_chapter(2, 5, 'selfpromo', remove=True),
            self._sponsor_chapter(4, 6, 'interaction', remove=True)]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([2], ['c']), [self._chapter(1, 6, remove=True)], False)

    def test_remove_marked_arrange_sponsors_ChapterWithRunsOfOverlappingSponsors(self):
        chapters = self._chapters([17], ['c']) + [
            self._sponsor_chapter(0, 3, 'intro'),
            self._sponsor_chapter(2, 5, 'sponsor'),
            self._sponsor_chapter(4, 6, 'selfpromo'),
            self._sponsor_chapter(7, 9, 'sponsor'),
            self._sponsor_chapter(8, 10, 'sponsor'),
            self._sponsor_chapter(9, 11, 'sponsor'),
            self._sponsor_chapter(12, 14, 'selfpromo'),
            self._sponsor_chapter(13, 16, 'interaction'),
            self._sponsor_chapter(15, 17, 'outro')]
        expected = self._chapters(
            [6, 7, 11, 12, 17],
            ['[SponsorBlock]: Intro/Sponsor/Self-Promotion', 'c - 1', '[SponsorBlock]: Sponsor',
             'c - 2', '[SponsorBlock]: Self-Promotion/Interaction Reminder/Outro'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_ChapterWithRunsOfOverlappingCuts(self):
        chapters = self._chapters([17], ['c']) + [
            self._chapter(0, 3, remove=True),
            self._sponsor_chapter(2, 5, 'sponsor', remove=True),
            self._chapter(4, 6, remove=True),
            self._sponsor_chapter(7, 9, 'sponsor', remove=True),
            self._chapter(8, 10, remove=True),
            self._chapter(9, 11, remove=True),
            self._sponsor_chapter(12, 14, 'sponsor', remove=True),
            self._sponsor_chapter(13, 16, 'selfpromo', remove=True),
            self._chapter(15, 17, remove=True)]
        expected_cuts = [self._chapter(0, 6, remove=True),
                         self._chapter(7, 11, remove=True),
                         self._chapter(12, 17, remove=True)]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([2], ['c']), expected_cuts, False)

    def test_remove_marked_arrange_sponsors_OverlappingSponsorsDifferentTitlesAfterCut(self):
        chapters = self._chapters([6], ['c']) + [
            self._sponsor_chapter(1, 6, 'sponsor'),
            self._sponsor_chapter(1, 4, 'intro'),
            self._sponsor_chapter(3, 5, 'interaction'),
            self._sponsor_chapter(3, 5, 'selfpromo', remove=True),
            self._sponsor_chapter(4, 5, 'interaction'),
            self._sponsor_chapter(5, 6, 'outro')]
        expected = self._chapters(
            [1, 3, 4], ['c', '[SponsorBlock]: Sponsor/Intro', '[SponsorBlock]: Sponsor/Outro'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(3, 5, remove=True)], True)

    def test_remove_marked_arrange_sponsors_SponsorsNoLongerOverlapAfterCut(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 3, 'sponsor'),
            self._sponsor_chapter(2, 5, 'interaction'),
            self._sponsor_chapter(3, 5, 'selpromo', remove=True),
            self._sponsor_chapter(4, 6, 'sponsor'),
            self._sponsor_chapter(5, 6, 'interaction')]
        expected = self._chapters(
            [1, 3, 4, 5], ['c - 1', '[SponsorBlock]: Sponsor/Interaction Reminder - 1',
                           '[SponsorBlock]: Sponsor/Interaction Reminder - 2', 'c - 2'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(3, 5, remove=True)], True)

    def test_remove_marked_arrange_sponsors_SponsorsStillOverlapAfterCut(self):
        chapters = self._chapters([7], ['c']) + [
            self._sponsor_chapter(1, 6, 'sponsor'),
            self._sponsor_chapter(2, 6, 'interaction'),
            self._sponsor_chapter(3, 5, 'selfpromo', remove=True)]
        expected = self._chapters(
            [1, 4, 5], ['c - 1', '[SponsorBlock]: Sponsor/Interaction Reminder', 'c - 2'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(3, 5, remove=True)], True)

    def test_remove_marked_arrange_sponsors_ChapterWithRunsOfOverlappingSponsorsAndCuts(self):
        chapters = self._chapters([20], ['c']) + [
            self._sponsor_chapter(1, 4, 'sponsor'),
            self._sponsor_chapter(1, 3, 'intro'),
            self._chapter(2, 3, remove=True),
            self._sponsor_chapter(3, 4, 'selfpromo'),
            self._sponsor_chapter(5, 7, 'sponsor'),
            self._sponsor_chapter(6, 8, 'interaction'),
            self._chapter(7, 8, remove=True),
            self._sponsor_chapter(7, 9, 'sponsor'),
            self._sponsor_chapter(8, 10, 'interaction'),
            self._sponsor_chapter(12, 17, 'selfpromo'),
            self._sponsor_chapter(13, 18, 'outro'),
            self._chapter(14, 15, remove=True),
            self._chapter(15, 16, remove=True)]
        expected = self._chapters(
            [1, 2, 3, 4, 6, 8, 10, 14, 16],
            ['c - 1', '[SponsorBlock]: Sponsor/Intro', '[SponsorBlock]: Sponsor/Self-Promotion',
             'c - 2', '[SponsorBlock]: Sponsor/Interaction Reminder - 1',
             '[SponsorBlock]: Sponsor/Interaction Reminder - 2', 'c - 3',
             '[SponsorBlock]: Self-Promotion/Outro', 'c - 4'])
        expected_cuts = [self._chapter(2, 3, remove=True),
                         self._chapter(7, 8, remove=True),
                         self._chapter(14, 16, remove=True)]
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, expected_cuts, True)

    def test_remove_marked_arrange_sponsors_SponsorOverlapsMultipleChapters(self):
        chapters = (self._chapters([2, 4, 6, 8, 10], ['c1', 'c2', 'c3', 'c4', 'c5'])
                    + [self._sponsor_chapter(1, 9, 'sponsor')])
        expected = self._chapters([1, 9, 10], ['c1', '[SponsorBlock]: Sponsor', 'c5'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_CutOverlapsMultipleChapters(self):
        cuts = [self._chapter(1, 9, remove=True)]
        chapters = self._chapters([2, 4, 6, 8, 10], ['c1', 'c2', 'c3', 'c4', 'c5']) + cuts
        expected = self._chapters([1, 2], ['c1', 'c5'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_SponsorsWithinSomeChaptersAndOverlappingOthers(self):
        chapters = (self._chapters([1, 4, 6, 8], ['c1', 'c2', 'c3', 'c4'])
                    + [self._sponsor_chapter(2, 3, 'sponsor'),
                       self._sponsor_chapter(5, 7, 'selfpromo')])
        expected = self._chapters([1, 2, 3, 4, 5, 7, 8],
                                  ['c1', 'c2 - 1', '[SponsorBlock]: Sponsor', 'c2 - 2', 'c3',
                                   '[SponsorBlock]: Self-Promotion', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_CutsWithinSomeChaptersAndOverlappingOthers(self):
        cuts = [self._chapter(2, 3, remove=True), self._chapter(5, 7, remove=True)]
        chapters = self._chapters([1, 4, 6, 8], ['c1', 'c2', 'c3', 'c4']) + cuts
        expected = self._chapters([1, 3, 4, 5], ['c1', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_ChaptersAfterLastSponsor(self):
        chapters = (self._chapters([2, 4, 5, 6], ['c1', 'c2', 'c3', 'c4'])
                    + [self._sponsor_chapter(1, 3, 'music_offtopic')])
        expected = self._chapters(
            [1, 3, 4, 5, 6],
            ['c1', '[SponsorBlock]: Non-Music Section', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_ChaptersAfterLastCut(self):
        cuts = [self._chapter(1, 3, remove=True)]
        chapters = self._chapters([2, 4, 5, 6], ['c1', 'c2', 'c3', 'c4']) + cuts
        expected = self._chapters([1, 2, 3, 4], ['c1', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_SponsorStartsAtChapterStart(self):
        chapters = (self._chapters([1, 2, 4], ['c1', 'c2', 'c3'])
                    + [self._sponsor_chapter(2, 3, 'sponsor')])
        expected = self._chapters([1, 2, 3, 4], ['c1', 'c2', '[SponsorBlock]: Sponsor', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_CutStartsAtChapterStart(self):
        cuts = [self._chapter(2, 3, remove=True)]
        chapters = self._chapters([1, 2, 4], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([1, 2, 3], ['c1', 'c2', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_SponsorEndsAtChapterEnd(self):
        chapters = (self._chapters([1, 3, 4], ['c1', 'c2', 'c3'])
                    + [self._sponsor_chapter(2, 3, 'sponsor')])
        expected = self._chapters([1, 2, 3, 4], ['c1', 'c2', '[SponsorBlock]: Sponsor', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_CutEndsAtChapterEnd(self):
        cuts = [self._chapter(2, 3, remove=True)]
        chapters = self._chapters([1, 3, 4], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([1, 2, 3], ['c1', 'c2', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_SponsorCoincidesWithChapters(self):
        chapters = (self._chapters([1, 2, 3, 4], ['c1', 'c2', 'c3', 'c4'])
                    + [self._sponsor_chapter(1, 3, 'sponsor')])
        expected = self._chapters([1, 3, 4], ['c1', '[SponsorBlock]: Sponsor', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_CutCoincidesWithChapters(self):
        cuts = [self._chapter(1, 3, remove=True)]
        chapters = self._chapters([1, 2, 3, 4], ['c1', 'c2', 'c3', 'c4']) + cuts
        expected = self._chapters([1, 2], ['c1', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_SponsorsAtVideoBoundaries(self):
        chapters = (self._chapters([2, 4, 6], ['c1', 'c2', 'c3'])
                    + [self._sponsor_chapter(0, 1, 'intro'), self._sponsor_chapter(5, 6, 'outro')])
        expected = self._chapters(
            [1, 2, 4, 5, 6], ['[SponsorBlock]: Intro', 'c1', 'c2', 'c3', '[SponsorBlock]: Outro'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_CutsAtVideoBoundaries(self):
        cuts = [self._chapter(0, 1, remove=True), self._chapter(5, 6, remove=True)]
        chapters = self._chapters([2, 4, 6], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([1, 3, 4], ['c1', 'c2', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_SponsorsOverlapChaptersAtVideoBoundaries(self):
        chapters = (self._chapters([1, 4, 5], ['c1', 'c2', 'c3'])
                    + [self._sponsor_chapter(0, 2, 'intro'), self._sponsor_chapter(3, 5, 'outro')])
        expected = self._chapters(
            [2, 3, 5], ['[SponsorBlock]: Intro', 'c2', '[SponsorBlock]: Outro'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_CutsOverlapChaptersAtVideoBoundaries(self):
        cuts = [self._chapter(0, 2, remove=True), self._chapter(3, 5, remove=True)]
        chapters = self._chapters([1, 4, 5], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([1], ['c2'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts, False)

    def test_remove_marked_arrange_sponsors_EverythingSponsored(self):
        chapters = (self._chapters([1, 2, 3, 4], ['c1', 'c2', 'c3', 'c4'])
                    + [self._sponsor_chapter(0, 2, 'intro'), self._sponsor_chapter(2, 4, 'outro')])
        expected = self._chapters([2, 4], ['[SponsorBlock]: Intro', '[SponsorBlock]: Outro'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [], True)

    def test_remove_marked_arrange_sponsors_EverythingCut(self):
        cuts = [self._chapter(0, 2, remove=True), self._chapter(2, 4, remove=True)]
        chapters = self._chapters([1, 2, 3, 4], ['c1', 'c2', 'c3', 'c4']) + cuts
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, [], [self._chapter(0, 4, remove=True)], False)

    def test_make_concat_opts_CommonCase(self):
        sponsor_chapters = [self._chapter(1, 2, 's1'), self._chapter(10, 20, 's2')]
        expected = '''ffconcat version 1.0
file 'file:test'
outpoint 1.000000
file 'file:test'
inpoint 2.000000
outpoint 10.000000
file 'file:test'
inpoint 20.000000
'''
        opts = self._pp._make_concat_opts(sponsor_chapters, 30)
        self.assertEqual(expected, ''.join(self._pp._concat_spec(['test'] * len(opts), opts)))

    def test_make_concat_opts_NoZeroDurationChunkAtVideoStart(self):
        sponsor_chapters = [self._chapter(0, 1, 's1'), self._chapter(10, 20, 's2')]
        expected = '''ffconcat version 1.0
file 'file:test'
inpoint 1.000000
outpoint 10.000000
file 'file:test'
inpoint 20.000000
'''
        opts = self._pp._make_concat_opts(sponsor_chapters, 30)
        self.assertEqual(expected, ''.join(self._pp._concat_spec(['test'] * len(opts), opts)))

    def test_make_concat_opts_NoZeroDurationChunkAtVideoEnd(self):
        sponsor_chapters = [self._chapter(1, 2, 's1'), self._chapter(10, 20, 's2')]
        expected = '''ffconcat version 1.0
file 'file:test'
outpoint 1.000000
file 'file:test'
inpoint 2.000000
outpoint 10.000000
'''
        opts = self._pp._make_concat_opts(sponsor_chapters, 20)
        self.assertEqual(expected, ''.join(self._pp._concat_spec(['test'] * len(opts), opts)))

    def test_quote_for_concat_RunsOfQuotes(self):
        self.assertEqual(
            r"'special '\'' '\'\''characters'\'\'\''galore'",
            self._pp._quote_for_concat("special ' ''characters'''galore"))

    def test_quote_for_concat_QuotesAtStart(self):
        self.assertEqual(
            r"\'\'\''special '\'' characters '\'' galore'",
            self._pp._quote_for_concat("'''special ' characters ' galore"))

    def test_quote_for_concat_QuotesAtEnd(self):
        self.assertEqual(
            r"'special '\'' characters '\'' galore'\'\'\'",
            self._pp._quote_for_concat("special ' characters ' galore'''"))
