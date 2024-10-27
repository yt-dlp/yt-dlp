#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import is_download_test, try_rm
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


def _download_restricted(url, filename, age):
    """ Returns true if the file has been downloaded """

    params = {
        'age_limit': age,
        'skip_download': True,
        'writeinfojson': True,
        'outtmpl': '%(id)s.%(ext)s',
    }
    ydl = YoutubeDL(params)
    ydl.add_default_info_extractors()
    json_filename = os.path.splitext(filename)[0] + '.info.json'
    try_rm(json_filename)
    try:
        ydl.download([url])
    except DownloadError:
        pass
    else:
        return os.path.exists(json_filename)
    finally:
        try_rm(json_filename)


@is_download_test
class TestAgeRestriction(unittest.TestCase):
    def _assert_restricted(self, url, filename, age, old_age=None):
        self.assertTrue(_download_restricted(url, filename, old_age))
        self.assertFalse(_download_restricted(url, filename, age))

    def test_youtube(self):
        self._assert_restricted('HtVdAasjOgU', 'HtVdAasjOgU.mp4', 10)

    def test_youporn(self):
        self._assert_restricted(
            'https://www.youporn.com/watch/16715086/sex-ed-in-detention-18-asmr/',
            '16715086.mp4', 2, old_age=25)


if __name__ == '__main__':
    unittest.main()
