#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import is_download_test, try_rm
from yt_dlp import YoutubeDL


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
    ydl.download([url])
    res = os.path.exists(json_filename)
    try_rm(json_filename)
    return res


@is_download_test
class TestAgeRestriction(unittest.TestCase):
    def _assert_restricted(self, url, filename, age, old_age=None):
        self.assertTrue(_download_restricted(url, filename, old_age))
        self.assertFalse(_download_restricted(url, filename, age))

    def test_youtube(self):
        self._assert_restricted('07FYdnEawAQ', '07FYdnEawAQ.mp4', 10)

    def test_youporn(self):
        self._assert_restricted(
            'http://www.youporn.com/watch/505835/sex-ed-is-it-safe-to-masturbate-daily/',
            '505835.mp4', 2, old_age=25)


if __name__ == '__main__':
    unittest.main()
