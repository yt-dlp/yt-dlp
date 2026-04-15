#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from yt_dlp.extractor.tviplayer import TVIPlayerIE


class TestTVIPlayerMisc(unittest.TestCase):
    def test_construct_video_url(self):
        assert_url = lambda video_id, suffix_len, expected: self.assertEqual(
            TVIPlayerIE._construct_video_url(video_id, suffix_len), expected)
        assert_url('69dd70230cf27f6588a68e86', 4,
                   'https://streaming-vod1.iol.pt/vod/8/e/8/6/smil:69dd70230cf27f6588a68e86-L.smil/playlist.m3u8')
        assert_url('69dd70230cf27f6588a68e86', 1,
                   'https://streaming-vod1.iol.pt/vod/6/smil:69dd70230cf27f6588a68e86-L.smil/playlist.m3u8')
        assert_url('69dd70230cf27f6588a68e86', 6,
                   'https://streaming-vod1.iol.pt/vod/a/6/8/e/8/6/smil:69dd70230cf27f6588a68e86-L.smil/playlist.m3u8')
        assert_url('68e255490cf29d28d828c8d9', 4,
                   'https://streaming-vod1.iol.pt/vod/c/8/d/9/smil:68e255490cf29d28d828c8d9-L.smil/playlist.m3u8')
        # default suffix_len is 4
        self.assertEqual(
            TVIPlayerIE._construct_video_url('69dd70230cf27f6588a68e86'),
            TVIPlayerIE._construct_video_url('69dd70230cf27f6588a68e86', 4))


if __name__ == '__main__':
    unittest.main()
