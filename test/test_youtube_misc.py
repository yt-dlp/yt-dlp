#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from yt_dlp import YoutubeDL
from yt_dlp.extractor import YoutubeIE, YoutubeTabIE
from yt_dlp.extractor.youtube._base import YoutubeBaseInfoExtractor


class TestYoutubeMisc(unittest.TestCase):
    def test_no_playlist_by_default(self):
        video_id = 'BaW_jenozKc'
        playlist_id = 'PLMYEtVRpaqY00V9W81Cwmzp6N6vZqfUKD4'
        with YoutubeDL({'quiet': True}, auto_init=False) as ydl:
            ie = YoutubeTabIE(ydl)
            with patch.object(ie, '_extract_data', side_effect=AssertionError('Playlist must not be fetched')) as extract_data:
                result = ie._real_extract(f'https://www.youtube.com/watch?v={video_id}&list={playlist_id}')
            extract_data.assert_not_called()
        self.assertEqual(result['_type'], 'url')
        self.assertEqual(result['url'], f'https://www.youtube.com/watch?v={video_id}')
        self.assertEqual(result['ie_key'], YoutubeIE.ie_key())

    def test_youtube_extract(self):
        assertExtractId = lambda url, video_id: self.assertEqual(YoutubeIE.extract_id(url), video_id)
        assertExtractId('http://www.youtube.com/watch?&v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('https://www.youtube.com/watch?&v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('https://www.youtube.com/watch?feature=player_embedded&v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('https://www.youtube.com/watch_popup?v=BaW_jenozKc', 'BaW_jenozKc')
        assertExtractId('http://www.youtube.com/watch?v=BaW_jenozKcsharePLED17F32AD9753930', 'BaW_jenozKc')
        assertExtractId('BaW_jenozKc', 'BaW_jenozKc')

    def test_extract_relative_time(self):
        ert = YoutubeBaseInfoExtractor.extract_relative_time

        # Abbreviated forms must equal their long-form equivalents.
        self.assertEqual(ert('5d ago'), ert('5 days ago'))
        self.assertEqual(ert('1mo ago'), ert('1 month ago'))
        self.assertEqual(ert('2mo ago'), ert('2 months ago'))
        self.assertEqual(ert('1y ago'), ert('1 year ago'))
        self.assertEqual(ert('1yr ago'), ert('1 year ago'))
        self.assertEqual(ert('3w ago'), ert('3 weeks ago'))
        self.assertEqual(ert('3wk ago'), ert('3 weeks ago'))

        self.assertIsNotNone(ert('30s ago'))
        self.assertIsNotNone(ert('30sec ago'))
        self.assertIsNotNone(ert('10min ago'))
        self.assertIsNotNone(ert('5h ago'))
        self.assertIsNotNone(ert('5hr ago'))

        self.assertIsNotNone(ert('today'))
        self.assertIsNotNone(ert('yesterday'))
        self.assertIsNotNone(ert('now'))

        self.assertEqual(ert('5 days ago'), ert('5 day ago'))

        self.assertIsNotNone(ert('streamed 6 days ago'))
        self.assertIsNotNone(ert('5 seconds ago (edited)'))
        self.assertIsNotNone(ert('updated today'))
        self.assertIsNotNone(ert('8 yr ago'))

        self.assertIsNone(ert('not a date string'))
        self.assertIsNone(ert(''))

        # Small safety check to prevent "drift".
        for unit in YoutubeBaseInfoExtractor._RELATIVE_TIME_UNIT_MAP:
            self.assertIsNotNone(ert(f'1 {unit} ago'), f'unit {unit!r} did not parse')


if __name__ == '__main__':
    unittest.main()
