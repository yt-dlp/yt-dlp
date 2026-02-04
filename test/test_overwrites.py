#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import subprocess

from test.helper import is_download_test, try_rm

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
download_file = os.path.join(root_dir, 'test.webm')


@is_download_test
class TestOverwrites(unittest.TestCase):
    def setUp(self):
        # create an empty file
        open(download_file, 'a').close()

    def test_default_overwrites(self):
        outp = subprocess.Popen(
            [
                sys.executable, 'yt_dlp/__main__.py',
                '-o', 'test.webm',
                'https://www.youtube.com/watch?v=jNQXAC9IVRw',
            ], cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sout, _ = outp.communicate()
        self.assertTrue(b'has already been downloaded' in sout)
        # if the file has no content, it has not been redownloaded
        self.assertTrue(os.path.getsize(download_file) < 1)

    def test_yes_overwrites(self):
        outp = subprocess.Popen(
            [
                sys.executable, 'yt_dlp/__main__.py', '--yes-overwrites',
                '-o', 'test.webm',
                'https://www.youtube.com/watch?v=jNQXAC9IVRw',
            ], cwd=root_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sout, _ = outp.communicate()
        self.assertTrue(b'has already been downloaded' not in sout)
        # if the file has no content, it has not been redownloaded
        self.assertTrue(os.path.getsize(download_file) > 1)

    def tearDown(self):
        try_rm(os.path.join(root_dir, 'test.webm'))


if __name__ == '__main__':
    unittest.main()
