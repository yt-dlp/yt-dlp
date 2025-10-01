import json
import unittest

from test.helper import FakeYDL

from yt_dlp.extractor.acfun import AcFunVideoIE


class TestAcFunPlaylist(unittest.TestCase):
    def setUp(self):
        self.ie = AcFunVideoIE()
        self.ie.set_downloader(FakeYDL({'noplaylist': False}))

    def test_playlist_entries_are_generated_for_multi_part_videos(self):
        video_info = {
            'title': 'Sample Playlist',
            'description': 'Sample description',
            'coverUrl': 'https://example.com/thumb.jpg',
            'user': {
                'name': 'Uploader Name',
                'href': 'uploader-id',
            },
            'videoList': [
                {
                    'id': 'part-1',
                    'title': 'Episode 1',
                },
                {
                    'id': 'part-2',
                    'title': 'Episode 2',
                },
            ],
            'currentVideoInfo': {
                'id': 'part-1',
            },
        }
        webpage = f'<script>window.videoInfo = {json.dumps(video_info)};</script>'
        self.ie._download_webpage = lambda url, video_id: webpage

        result = self.ie._real_extract('https://www.acfun.cn/v/ac12345?foo=bar')

        self.assertEqual(result['_type'], 'playlist')
        self.assertEqual(result['id'], '12345')
        self.assertEqual(result['title'], 'Sample Playlist')
        self.assertEqual(result['description'], 'Sample description')
        self.assertEqual(result['uploader'], 'Uploader Name')
        self.assertEqual(result['uploader_id'], 'uploader-id')
        entry_urls = [entry['url'] for entry in result['entries']]
        entry_ids = [entry['id'] for entry in result['entries']]
        entry_titles = [entry['title'] for entry in result['entries']]

        self.assertEqual(
            entry_urls,
            [
                'https://www.acfun.cn/v/ac12345?foo=bar',
                'https://www.acfun.cn/v/ac12345_2?foo=bar',
            ],
        )
        self.assertEqual(entry_ids, ['12345', '12345_2'])
        self.assertEqual(entry_titles, ['Episode 1', 'Episode 2'])
        self.assertTrue(all(entry['ie_key'] == 'AcFunVideo' for entry in result['entries']))
