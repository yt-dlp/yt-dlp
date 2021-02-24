#!/usr/bin/env python
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL


from yt_dlp.extractor import (
    YoutubePlaylistIE,
    YoutubeTabIE,
    YoutubeIE,
)


class TestYoutubeLists(unittest.TestCase):
    def assertIsPlaylist(self, info):
        """Make sure the info has '_type' set to 'playlist'"""
        self.assertEqual(info['_type'], 'playlist')

    def test_youtube_playlist_noplaylist(self):
        dl = FakeYDL()
        dl.params['noplaylist'] = True
        ie = YoutubePlaylistIE(dl)
        result = ie.extract('https://www.youtube.com/watch?v=FXxLjLQi3Fg&list=PLwiyx1dc3P2JR9N8gQaQN_BCvlSlap7re')
        self.assertEqual(result['_type'], 'url')
        self.assertEqual(YoutubeIE().extract_id(result['url']), 'FXxLjLQi3Fg')

    def test_youtube_course(self):
        dl = FakeYDL()
        ie = YoutubePlaylistIE(dl)
        # TODO find a > 100 (paginating?) videos course
        result = ie.extract('https://www.youtube.com/course?list=ECUl4u3cNGP61MdtwGTqZA0MreSaDybji8')
        entries = list(result['entries'])
        self.assertEqual(YoutubeIE().extract_id(entries[0]['url']), 'j9WZyLZCBzs')
        self.assertEqual(len(entries), 25)
        self.assertEqual(YoutubeIE().extract_id(entries[-1]['url']), 'rYefUsYuEp0')

    def test_youtube_mix(self):
        dl = FakeYDL()
        ie = YoutubePlaylistIE(dl)
        result = ie.extract('https://www.youtube.com/watch?v=W01L70IGBgE&index=2&list=RDOQpdSVF_k_w')
        entries = result['entries']
        self.assertTrue(len(entries) >= 50)
        original_video = entries[0]
        self.assertEqual(original_video['id'], 'OQpdSVF_k_w')

    def test_youtube_toptracks(self):
        print('Skipping: The playlist page gives error 500')
        return
        dl = FakeYDL()
        ie = YoutubePlaylistIE(dl)
        result = ie.extract('https://www.youtube.com/playlist?list=MCUS')
        entries = result['entries']
        self.assertEqual(len(entries), 100)

    def test_youtube_flat_playlist_extraction(self):
        dl = FakeYDL()
        dl.params['extract_flat'] = True
        ie = YoutubeTabIE(dl)
        result = ie.extract('https://www.youtube.com/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc')
        self.assertIsPlaylist(result)
        entries = list(result['entries'])
        self.assertTrue(len(entries) == 1)
        video = entries[0]
        self.assertEqual(video['_type'], 'url_transparent')
        self.assertEqual(video['ie_key'], 'Youtube')
        self.assertEqual(video['id'], 'BaW_jenozKc')
        self.assertEqual(video['url'], 'BaW_jenozKc')
        self.assertEqual(video['title'], 'youtube-dl test video "\'/\\ä↭𝕐')
        self.assertEqual(video['duration'], 10)
        self.assertEqual(video['uploader'], 'Philipp Hagemeister')


if __name__ == '__main__':
    unittest.main()
