#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import subprocess

from yt_dlp import YoutubeDL
from yt_dlp.utils import shell_quote
from yt_dlp.postprocessor import (
    ExecPP,
    FFmpegThumbnailsConvertorPP,
    MetadataFromFieldPP,
    MetadataParserPP,
    ModifyChaptersPP,
    SponsorBlockPP,
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

        test_data_dir = 'test/testdata/thumbnails'
        generated_file = f'{test_data_dir}/empty.webp'

        subprocess.check_call([
            pp.executable, '-y', '-f', 'lavfi', '-i', 'color=c=black:s=320x320',
            '-c:v', 'libwebp', '-pix_fmt', 'yuv420p', '-vframes', '1', generated_file,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        file = test_data_dir + '/foo %d bar/foo_%d.{}'
        initial_file = file.format('webp')
        os.replace(generated_file, initial_file)

        tests = (('webp', 'png'), ('png', 'jpg'))

        for inp, out in tests:
            out_file = file.format(out)
            if os.path.exists(out_file):
                os.remove(out_file)
            pp.convert_thumbnail(file.format(inp), out)
            self.assertTrue(os.path.exists(out_file))

        for _, out in tests:
            os.remove(file.format(out))

        os.remove(initial_file)


class TestExec(unittest.TestCase):
    def test_parse_cmd(self):
        pp = ExecPP(YoutubeDL(), '')
        info = {'filepath': 'file name'}
        cmd = 'echo {}'.format(shell_quote(info['filepath']))

        self.assertEqual(pp.parse_cmd('echo', info), cmd)
        self.assertEqual(pp.parse_cmd('echo {}', info), cmd)
        self.assertEqual(pp.parse_cmd('echo %(filepath)q', info), cmd)


class TestModifyChaptersPP(unittest.TestCase):
    def setUp(self):
        self._pp = ModifyChaptersPP(YoutubeDL())

    @staticmethod
    def _sponsor_chapter(start, end, cat, remove=False, title=None):
        if title is None:
            title = SponsorBlockPP.CATEGORIES[cat]
        return {
            'start_time': start,
            'end_time': end,
            '_categories': [(cat, start, end, title)],
            **({'remove': True} if remove else {}),
        }

    @staticmethod
    def _chapter(start, end, title=None, remove=False):
        c = {'start_time': start, 'end_time': end}
        if title is not None:
            c['title'] = title
        if remove:
            c['remove'] = True
        return c

    def _chapters(self, ends, titles):
        self.assertEqual(len(ends), len(titles))
        start = 0
        chapters = []
        for e, t in zip(ends, titles):
            chapters.append(self._chapter(start, e, t))
            start = e
        return chapters

    def _remove_marked_arrange_sponsors_test_impl(
            self, chapters, expected_chapters, expected_removed):
        actual_chapters, actual_removed = (
            self._pp._remove_marked_arrange_sponsors(chapters))
        for c in actual_removed:
            c.pop('title', None)
            c.pop('_categories', None)
        actual_chapters = [{
            'start_time': c['start_time'],
            'end_time': c['end_time'],
            'title': c['title'],
        } for c in actual_chapters]
        self.assertSequenceEqual(expected_chapters, actual_chapters)
        self.assertSequenceEqual(expected_removed, actual_removed)

    def test_remove_marked_arrange_sponsors_CanGetThroughUnaltered(self):
        chapters = self._chapters([10, 20, 30, 40], ['c1', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, chapters, [])

    def test_remove_marked_arrange_sponsors_ChapterWithSponsors(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 20, 'sponsor'),
            self._sponsor_chapter(30, 40, 'preview'),
            self._sponsor_chapter(50, 60, 'filler')]
        expected = self._chapters(
            [10, 20, 30, 40, 50, 60, 70],
            ['c', '[SponsorBlock]: Sponsor', 'c', '[SponsorBlock]: Preview/Recap',
             'c', '[SponsorBlock]: Filler Tangent', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_SponsorBlockChapters(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 20, 'chapter', title='sb c1'),
            self._sponsor_chapter(15, 16, 'chapter', title='sb c2'),
            self._sponsor_chapter(30, 40, 'preview'),
            self._sponsor_chapter(50, 60, 'filler')]
        expected = self._chapters(
            [10, 15, 16, 20, 30, 40, 50, 60, 70],
            ['c', '[SponsorBlock]: sb c1', '[SponsorBlock]: sb c1, sb c2', '[SponsorBlock]: sb c1',
             'c', '[SponsorBlock]: Preview/Recap',
             'c', '[SponsorBlock]: Filler Tangent', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_UniqueNamesForOverlappingSponsors(self):
        chapters = [
            *self._chapters([120], ['c']),
            self._sponsor_chapter(10, 45, 'sponsor'),
            self._sponsor_chapter(20, 40, 'selfpromo'),
            self._sponsor_chapter(50, 70, 'sponsor'),
            self._sponsor_chapter(60, 85, 'selfpromo'),
            self._sponsor_chapter(90, 120, 'selfpromo'),
            self._sponsor_chapter(100, 110, 'sponsor')]
        expected = self._chapters(
            [10, 20, 40, 45, 50, 60, 70, 85, 90, 100, 110, 120],
            ['c', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Sponsor, Unpaid/Self Promotion',
             '[SponsorBlock]: Sponsor',
             'c', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Sponsor, Unpaid/Self Promotion',
             '[SponsorBlock]: Unpaid/Self Promotion',
             'c', '[SponsorBlock]: Unpaid/Self Promotion', '[SponsorBlock]: Unpaid/Self Promotion, Sponsor',
             '[SponsorBlock]: Unpaid/Self Promotion'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_ChapterWithCuts(self):
        cuts = [self._chapter(10, 20, remove=True),
                self._sponsor_chapter(30, 40, 'sponsor', remove=True),
                self._chapter(50, 60, remove=True)]
        chapters = self._chapters([70], ['c']) + cuts
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([40], ['c']), cuts)

    def test_remove_marked_arrange_sponsors_ChapterWithSponsorsAndCuts(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 20, 'sponsor'),
            self._sponsor_chapter(30, 40, 'selfpromo', remove=True),
            self._sponsor_chapter(50, 60, 'interaction')]
        expected = self._chapters([10, 20, 40, 50, 60],
                                  ['c', '[SponsorBlock]: Sponsor', 'c',
                                   '[SponsorBlock]: Interaction Reminder', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(30, 40, remove=True)])

    def test_remove_marked_arrange_sponsors_ChapterWithSponsorCutInTheMiddle(self):
        cuts = [self._sponsor_chapter(20, 30, 'selfpromo', remove=True),
                self._chapter(40, 50, remove=True)]
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 60, 'sponsor'),
            *cuts]
        expected = self._chapters(
            [10, 40, 50], ['c', '[SponsorBlock]: Sponsor', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_ChapterWithCutHidingSponsor(self):
        cuts = [self._sponsor_chapter(20, 50, 'selfpromo', remove=True)]
        chapters = [
            *self._chapters([60], ['c']),
            self._sponsor_chapter(10, 20, 'intro'),
            self._sponsor_chapter(30, 40, 'sponsor'),
            self._sponsor_chapter(50, 60, 'outro'),
            *cuts]
        expected = self._chapters(
            [10, 20, 30], ['c', '[SponsorBlock]: Intermission/Intro Animation', '[SponsorBlock]: Endcards/Credits'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_ChapterWithAdjacentSponsors(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 20, 'sponsor'),
            self._sponsor_chapter(20, 30, 'selfpromo'),
            self._sponsor_chapter(30, 40, 'interaction')]
        expected = self._chapters(
            [10, 20, 30, 40, 70],
            ['c', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Unpaid/Self Promotion',
             '[SponsorBlock]: Interaction Reminder', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_ChapterWithAdjacentCuts(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 20, 'sponsor'),
            self._sponsor_chapter(20, 30, 'interaction', remove=True),
            self._chapter(30, 40, remove=True),
            self._sponsor_chapter(40, 50, 'selfpromo', remove=True),
            self._sponsor_chapter(50, 60, 'interaction')]
        expected = self._chapters([10, 20, 30, 40],
                                  ['c', '[SponsorBlock]: Sponsor',
                                   '[SponsorBlock]: Interaction Reminder', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(20, 50, remove=True)])

    def test_remove_marked_arrange_sponsors_ChapterWithOverlappingSponsors(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 30, 'sponsor'),
            self._sponsor_chapter(20, 50, 'selfpromo'),
            self._sponsor_chapter(40, 60, 'interaction')]
        expected = self._chapters(
            [10, 20, 30, 40, 50, 60, 70],
            ['c', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Sponsor, Unpaid/Self Promotion',
             '[SponsorBlock]: Unpaid/Self Promotion', '[SponsorBlock]: Unpaid/Self Promotion, Interaction Reminder',
             '[SponsorBlock]: Interaction Reminder', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_ChapterWithOverlappingCuts(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 30, 'sponsor', remove=True),
            self._sponsor_chapter(20, 50, 'selfpromo', remove=True),
            self._sponsor_chapter(40, 60, 'interaction', remove=True)]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([20], ['c']), [self._chapter(10, 60, remove=True)])

    def test_remove_marked_arrange_sponsors_ChapterWithRunsOfOverlappingSponsors(self):
        chapters = [
            *self._chapters([170], ['c']),
            self._sponsor_chapter(0, 30, 'intro'),
            self._sponsor_chapter(20, 50, 'sponsor'),
            self._sponsor_chapter(40, 60, 'selfpromo'),
            self._sponsor_chapter(70, 90, 'sponsor'),
            self._sponsor_chapter(80, 100, 'sponsor'),
            self._sponsor_chapter(90, 110, 'sponsor'),
            self._sponsor_chapter(120, 140, 'selfpromo'),
            self._sponsor_chapter(130, 160, 'interaction'),
            self._sponsor_chapter(150, 170, 'outro')]
        expected = self._chapters(
            [20, 30, 40, 50, 60, 70, 110, 120, 130, 140, 150, 160, 170],
            ['[SponsorBlock]: Intermission/Intro Animation', '[SponsorBlock]: Intermission/Intro Animation, Sponsor', '[SponsorBlock]: Sponsor',
             '[SponsorBlock]: Sponsor, Unpaid/Self Promotion', '[SponsorBlock]: Unpaid/Self Promotion', 'c',
             '[SponsorBlock]: Sponsor', 'c', '[SponsorBlock]: Unpaid/Self Promotion',
             '[SponsorBlock]: Unpaid/Self Promotion, Interaction Reminder',
             '[SponsorBlock]: Interaction Reminder',
             '[SponsorBlock]: Interaction Reminder, Endcards/Credits', '[SponsorBlock]: Endcards/Credits'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_ChapterWithRunsOfOverlappingCuts(self):
        chapters = [
            *self._chapters([170], ['c']),
            self._chapter(0, 30, remove=True),
            self._sponsor_chapter(20, 50, 'sponsor', remove=True),
            self._chapter(40, 60, remove=True),
            self._sponsor_chapter(70, 90, 'sponsor', remove=True),
            self._chapter(80, 100, remove=True),
            self._chapter(90, 110, remove=True),
            self._sponsor_chapter(120, 140, 'sponsor', remove=True),
            self._sponsor_chapter(130, 160, 'selfpromo', remove=True),
            self._chapter(150, 170, remove=True)]
        expected_cuts = [self._chapter(0, 60, remove=True),
                         self._chapter(70, 110, remove=True),
                         self._chapter(120, 170, remove=True)]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([20], ['c']), expected_cuts)

    def test_remove_marked_arrange_sponsors_OverlappingSponsorsDifferentTitlesAfterCut(self):
        chapters = [
            *self._chapters([60], ['c']),
            self._sponsor_chapter(10, 60, 'sponsor'),
            self._sponsor_chapter(10, 40, 'intro'),
            self._sponsor_chapter(30, 50, 'interaction'),
            self._sponsor_chapter(30, 50, 'selfpromo', remove=True),
            self._sponsor_chapter(40, 50, 'interaction'),
            self._sponsor_chapter(50, 60, 'outro')]
        expected = self._chapters(
            [10, 30, 40], ['c', '[SponsorBlock]: Sponsor, Intermission/Intro Animation', '[SponsorBlock]: Sponsor, Endcards/Credits'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(30, 50, remove=True)])

    def test_remove_marked_arrange_sponsors_SponsorsNoLongerOverlapAfterCut(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 30, 'sponsor'),
            self._sponsor_chapter(20, 50, 'interaction'),
            self._sponsor_chapter(30, 50, 'selfpromo', remove=True),
            self._sponsor_chapter(40, 60, 'sponsor'),
            self._sponsor_chapter(50, 60, 'interaction')]
        expected = self._chapters(
            [10, 20, 40, 50], ['c', '[SponsorBlock]: Sponsor',
                               '[SponsorBlock]: Sponsor, Interaction Reminder', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(30, 50, remove=True)])

    def test_remove_marked_arrange_sponsors_SponsorsStillOverlapAfterCut(self):
        chapters = [
            *self._chapters([70], ['c']),
            self._sponsor_chapter(10, 60, 'sponsor'),
            self._sponsor_chapter(20, 60, 'interaction'),
            self._sponsor_chapter(30, 50, 'selfpromo', remove=True)]
        expected = self._chapters(
            [10, 20, 40, 50], ['c', '[SponsorBlock]: Sponsor',
                               '[SponsorBlock]: Sponsor, Interaction Reminder', 'c'])
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, expected, [self._chapter(30, 50, remove=True)])

    def test_remove_marked_arrange_sponsors_ChapterWithRunsOfOverlappingSponsorsAndCuts(self):
        chapters = [
            *self._chapters([200], ['c']),
            self._sponsor_chapter(10, 40, 'sponsor'),
            self._sponsor_chapter(10, 30, 'intro'),
            self._chapter(20, 30, remove=True),
            self._sponsor_chapter(30, 40, 'selfpromo'),
            self._sponsor_chapter(50, 70, 'sponsor'),
            self._sponsor_chapter(60, 80, 'interaction'),
            self._chapter(70, 80, remove=True),
            self._sponsor_chapter(70, 90, 'sponsor'),
            self._sponsor_chapter(80, 100, 'interaction'),
            self._sponsor_chapter(120, 170, 'selfpromo'),
            self._sponsor_chapter(130, 180, 'outro'),
            self._chapter(140, 150, remove=True),
            self._chapter(150, 160, remove=True)]
        expected = self._chapters(
            [10, 20, 30, 40, 50, 70, 80, 100, 110, 130, 140, 160],
            ['c', '[SponsorBlock]: Sponsor, Intermission/Intro Animation', '[SponsorBlock]: Sponsor, Unpaid/Self Promotion',
             'c', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Sponsor, Interaction Reminder',
             '[SponsorBlock]: Interaction Reminder', 'c', '[SponsorBlock]: Unpaid/Self Promotion',
             '[SponsorBlock]: Unpaid/Self Promotion, Endcards/Credits', '[SponsorBlock]: Endcards/Credits', 'c'])
        expected_cuts = [self._chapter(20, 30, remove=True),
                         self._chapter(70, 80, remove=True),
                         self._chapter(140, 160, remove=True)]
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, expected_cuts)

    def test_remove_marked_arrange_sponsors_SponsorOverlapsMultipleChapters(self):
        chapters = [
            *self._chapters([20, 40, 60, 80, 100], ['c1', 'c2', 'c3', 'c4', 'c5']),
            self._sponsor_chapter(10, 90, 'sponsor')]
        expected = self._chapters([10, 90, 100], ['c1', '[SponsorBlock]: Sponsor', 'c5'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_CutOverlapsMultipleChapters(self):
        cuts = [self._chapter(10, 90, remove=True)]
        chapters = self._chapters([20, 40, 60, 80, 100], ['c1', 'c2', 'c3', 'c4', 'c5']) + cuts
        expected = self._chapters([10, 20], ['c1', 'c5'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_SponsorsWithinSomeChaptersAndOverlappingOthers(self):
        chapters = [
            *self._chapters([10, 40, 60, 80], ['c1', 'c2', 'c3', 'c4']),
            self._sponsor_chapter(20, 30, 'sponsor'),
            self._sponsor_chapter(50, 70, 'selfpromo')]
        expected = self._chapters([10, 20, 30, 40, 50, 70, 80],
                                  ['c1', 'c2', '[SponsorBlock]: Sponsor', 'c2', 'c3',
                                   '[SponsorBlock]: Unpaid/Self Promotion', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_CutsWithinSomeChaptersAndOverlappingOthers(self):
        cuts = [self._chapter(20, 30, remove=True), self._chapter(50, 70, remove=True)]
        chapters = self._chapters([10, 40, 60, 80], ['c1', 'c2', 'c3', 'c4']) + cuts
        expected = self._chapters([10, 30, 40, 50], ['c1', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_ChaptersAfterLastSponsor(self):
        chapters = [
            *self._chapters([20, 40, 50, 60], ['c1', 'c2', 'c3', 'c4']),
            self._sponsor_chapter(10, 30, 'music_offtopic')]
        expected = self._chapters(
            [10, 30, 40, 50, 60],
            ['c1', '[SponsorBlock]: Non-Music Section', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_ChaptersAfterLastCut(self):
        cuts = [self._chapter(10, 30, remove=True)]
        chapters = self._chapters([20, 40, 50, 60], ['c1', 'c2', 'c3', 'c4']) + cuts
        expected = self._chapters([10, 20, 30, 40], ['c1', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_SponsorStartsAtChapterStart(self):
        chapters = [
            *self._chapters([10, 20, 40], ['c1', 'c2', 'c3']),
            self._sponsor_chapter(20, 30, 'sponsor')]
        expected = self._chapters([10, 20, 30, 40], ['c1', 'c2', '[SponsorBlock]: Sponsor', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_CutStartsAtChapterStart(self):
        cuts = [self._chapter(20, 30, remove=True)]
        chapters = self._chapters([10, 20, 40], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([10, 20, 30], ['c1', 'c2', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_SponsorEndsAtChapterEnd(self):
        chapters = [
            *self._chapters([10, 30, 40], ['c1', 'c2', 'c3']),
            self._sponsor_chapter(20, 30, 'sponsor')]
        expected = self._chapters([10, 20, 30, 40], ['c1', 'c2', '[SponsorBlock]: Sponsor', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_CutEndsAtChapterEnd(self):
        cuts = [self._chapter(20, 30, remove=True)]
        chapters = self._chapters([10, 30, 40], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([10, 20, 30], ['c1', 'c2', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_SponsorCoincidesWithChapters(self):
        chapters = [
            *self._chapters([10, 20, 30, 40], ['c1', 'c2', 'c3', 'c4']),
            self._sponsor_chapter(10, 30, 'sponsor')]
        expected = self._chapters([10, 30, 40], ['c1', '[SponsorBlock]: Sponsor', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_CutCoincidesWithChapters(self):
        cuts = [self._chapter(10, 30, remove=True)]
        chapters = self._chapters([10, 20, 30, 40], ['c1', 'c2', 'c3', 'c4']) + cuts
        expected = self._chapters([10, 20], ['c1', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_SponsorsAtVideoBoundaries(self):
        chapters = [
            *self._chapters([20, 40, 60], ['c1', 'c2', 'c3']),
            self._sponsor_chapter(0, 10, 'intro'), self._sponsor_chapter(50, 60, 'outro')]
        expected = self._chapters(
            [10, 20, 40, 50, 60], ['[SponsorBlock]: Intermission/Intro Animation', 'c1', 'c2', 'c3', '[SponsorBlock]: Endcards/Credits'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_CutsAtVideoBoundaries(self):
        cuts = [self._chapter(0, 10, remove=True), self._chapter(50, 60, remove=True)]
        chapters = self._chapters([20, 40, 60], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([10, 30, 40], ['c1', 'c2', 'c3'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_SponsorsOverlapChaptersAtVideoBoundaries(self):
        chapters = [
            *self._chapters([10, 40, 50], ['c1', 'c2', 'c3']),
            self._sponsor_chapter(0, 20, 'intro'),
            self._sponsor_chapter(30, 50, 'outro')]
        expected = self._chapters(
            [20, 30, 50], ['[SponsorBlock]: Intermission/Intro Animation', 'c2', '[SponsorBlock]: Endcards/Credits'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_CutsOverlapChaptersAtVideoBoundaries(self):
        cuts = [self._chapter(0, 20, remove=True), self._chapter(30, 50, remove=True)]
        chapters = self._chapters([10, 40, 50], ['c1', 'c2', 'c3']) + cuts
        expected = self._chapters([10], ['c2'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, cuts)

    def test_remove_marked_arrange_sponsors_EverythingSponsored(self):
        chapters = [
            *self._chapters([10, 20, 30, 40], ['c1', 'c2', 'c3', 'c4']),
            self._sponsor_chapter(0, 20, 'intro'),
            self._sponsor_chapter(20, 40, 'outro')]
        expected = self._chapters([20, 40], ['[SponsorBlock]: Intermission/Intro Animation', '[SponsorBlock]: Endcards/Credits'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, expected, [])

    def test_remove_marked_arrange_sponsors_EverythingCut(self):
        cuts = [self._chapter(0, 20, remove=True), self._chapter(20, 40, remove=True)]
        chapters = self._chapters([10, 20, 30, 40], ['c1', 'c2', 'c3', 'c4']) + cuts
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, [], [self._chapter(0, 40, remove=True)])

    def test_remove_marked_arrange_sponsors_TinyChaptersInTheOriginalArePreserved(self):
        chapters = self._chapters([0.1, 0.2, 0.3, 0.4], ['c1', 'c2', 'c3', 'c4'])
        self._remove_marked_arrange_sponsors_test_impl(chapters, chapters, [])

    def test_remove_marked_arrange_sponsors_TinySponsorsAreIgnored(self):
        chapters = [self._sponsor_chapter(0, 0.1, 'intro'), self._chapter(0.1, 0.2, 'c1'),
                    self._sponsor_chapter(0.2, 0.3, 'sponsor'), self._chapter(0.3, 0.4, 'c2'),
                    self._sponsor_chapter(0.4, 0.5, 'outro')]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([0.3, 0.5], ['c1', 'c2']), [])

    def test_remove_marked_arrange_sponsors_TinyChaptersResultingFromCutsAreIgnored(self):
        cuts = [self._chapter(1.5, 2.5, remove=True)]
        chapters = self._chapters([2, 3, 3.5], ['c1', 'c2', 'c3']) + cuts
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([2, 2.5], ['c1', 'c3']), cuts)

    def test_remove_marked_arrange_sponsors_SingleTinyChapterIsPreserved(self):
        cuts = [self._chapter(0.5, 2, remove=True)]
        chapters = self._chapters([2], ['c']) + cuts
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([0.5], ['c']), cuts)

    def test_remove_marked_arrange_sponsors_TinyChapterAtTheStartPrependedToTheNext(self):
        cuts = [self._chapter(0.5, 2, remove=True)]
        chapters = self._chapters([2, 4], ['c1', 'c2']) + cuts
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([2.5], ['c2']), cuts)

    def test_remove_marked_arrange_sponsors_TinyChaptersResultingFromSponsorOverlapAreIgnored(self):
        chapters = [
            *self._chapters([1, 3, 4], ['c1', 'c2', 'c3']),
            self._sponsor_chapter(1.5, 2.5, 'sponsor')]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([1.5, 2.5, 4], ['c1', '[SponsorBlock]: Sponsor', 'c3']), [])

    def test_remove_marked_arrange_sponsors_TinySponsorsOverlapsAreIgnored(self):
        chapters = [
            *self._chapters([2, 3, 5], ['c1', 'c2', 'c3']),
            self._sponsor_chapter(1, 3, 'sponsor'),
            self._sponsor_chapter(2.5, 4, 'selfpromo')]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([1, 3, 4, 5], [
                'c1', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Unpaid/Self Promotion', 'c3']), [])

    def test_remove_marked_arrange_sponsors_TinySponsorsPrependedToTheNextSponsor(self):
        chapters = [
            *self._chapters([4], ['c']),
            self._sponsor_chapter(1.5, 2, 'sponsor'),
            self._sponsor_chapter(2, 4, 'selfpromo')]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([1.5, 4], ['c', '[SponsorBlock]: Unpaid/Self Promotion']), [])

    def test_remove_marked_arrange_sponsors_SmallestSponsorInTheOverlapGetsNamed(self):
        self._pp._sponsorblock_chapter_title = '[SponsorBlock]: %(name)s'
        chapters = [
            *self._chapters([10], ['c']),
            self._sponsor_chapter(2, 8, 'sponsor'),
            self._sponsor_chapter(4, 6, 'selfpromo')]
        self._remove_marked_arrange_sponsors_test_impl(
            chapters, self._chapters([2, 4, 6, 8, 10], [
                'c', '[SponsorBlock]: Sponsor', '[SponsorBlock]: Unpaid/Self Promotion',
                '[SponsorBlock]: Sponsor', 'c',
            ]), [])

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
            self._pp._quote_for_ffmpeg("special ' ''characters'''galore"))

    def test_quote_for_concat_QuotesAtStart(self):
        self.assertEqual(
            r"\'\'\''special '\'' characters '\'' galore'",
            self._pp._quote_for_ffmpeg("'''special ' characters ' galore"))

    def test_quote_for_concat_QuotesAtEnd(self):
        self.assertEqual(
            r"'special '\'' characters '\'' galore'\'\'\'",
            self._pp._quote_for_ffmpeg("special ' characters ' galore'''"))


if __name__ == '__main__':
    unittest.main()
