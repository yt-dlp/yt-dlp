#!/usr/bin/env python3
# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL, is_download_test

from yt_dlp.extractor import YoutubeIE, YoutubeTabIE


@is_download_test
class TestYoutubeLists(unittest.TestCase):
    def assertIsPlaylist(self, info):
        """Make sure the info has '_type' set to 'playlist'"""
        self.assertEqual(info['_type'], 'playlist')

    def test_youtube_playlist_noplaylist(self):
        dl = FakeYDL()
        dl.params['noplaylist'] = True
        ie = YoutubeTabIE(dl)
        result = ie.extract('https://www.youtube.com/watch?v=OmJ-4B-mS-Y&list=PLydZ2Hrp_gPRJViZjLFKaBMgCQOYEEkyp&index=2')
        self.assertEqual(result['_type'], 'url')
        self.assertEqual(result['ie_key'], YoutubeIE.ie_key())
        self.assertEqual(YoutubeIE.extract_id(result['url']), 'OmJ-4B-mS-Y')

    def test_youtube_mix(self):
        dl = FakeYDL()
        ie = YoutubeTabIE(dl)
        result = ie.extract('https://www.youtube.com/watch?v=tyITL_exICo&list=RDCLAK5uy_kLWIr9gv1XLlPbaDS965-Db4TrBoUTxQ8')
        entries = list(result['entries'])
        self.assertTrue(len(entries) >= 50)
        original_video = entries[0]
        self.assertEqual(original_video['id'], 'tyITL_exICo')

    def test_youtube_flat_playlist_extraction(self):
        dl = FakeYDL()
        dl.params['extract_flat'] = True
        ie = YoutubeTabIE(dl)
        result = ie.extract('https://www.youtube.com/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc')
        self.assertIsPlaylist(result)
        entries = list(result['entries'])
        self.assertTrue(len(entries) == 1)
        video = entries[0]
        self.assertEqual(video['_type'], 'url')
        self.assertEqual(video['ie_key'], 'Youtube')
        self.assertEqual(video['id'], 'BaW_jenozKc')
        self.assertEqual(video['url'], 'https://www.youtube.com/watch?v=BaW_jenozKc')
        self.assertEqual(video['title'], 'youtube-dl test video "\'/\\ä↭𝕐')
        self.assertEqual(video['duration'], 10)
        self.assertEqual(video['uploader'], 'Philipp Hagemeister')


if __name__ == '__main__':
    unittest.main()
