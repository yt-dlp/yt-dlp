#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import http_server_port
from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_http_server
from yt_dlp.downloader import HlsFD
import subprocess
import threading

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TEST_DIR, 'testdata', 'hls')


class HTTPTestRequestHandler(compat_http_server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DATA_DIR, **kwargs)


class FakeLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class TestHLS(unittest.TestCase):
    def setUp(self):
        self.httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 8000), HTTPTestRequestHandler)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def tearDown(self):
        self.httpd.server_close()
        self.httpd.shutdown()

    def doCleanups(self):
        for file in ['destination.mp4',
                     'out.m3u8', 'out0.ts', 'out1.ts', 'out2.ts', 'out3.ts', 'out4.ts', 'out5.ts', 'out6.ts']:
            try:
                os.remove(os.path.join(DATA_DIR, '_'.join((self._testMethodName, file))))
            except (FileNotFoundError, IsADirectoryError):
                pass

    def test_real_download_noiv(self):
        out_filename = '%s_out.m3u8' % self._testMethodName
        key_info_filename = '%s_file.keyinfo' % self._testMethodName

        was_error = False
        try:
            handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=65',
                                       '-hls_key_info_file', key_info_filename, out_filename],
                                      cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.fail("Error occurred during generating files.")

        ydl = YoutubeDL({'logger': FakeLogger()})
        downloader = HlsFD(ydl, {})
        info_dict = {
            'url': 'http://127.0.0.1:%d/%s_out.m3u8' % (self.port, self._testMethodName),
            'ext': 'mp4'
        }
        r = downloader.real_download(os.path.join(DATA_DIR, '%s_destination.mp4' % self._testMethodName), info_dict)
        self.assertTrue(r)

    def test_real_download_iv(self):
        out_filename = '%s_out.m3u8' % self._testMethodName
        key_info_filename = '%s_file.keyinfo' % self._testMethodName

        was_error = False
        try:
            handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=65',
                                       '-hls_key_info_file', key_info_filename, out_filename],
                                      cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.fail("Error occurred during generating files.")

        ydl = YoutubeDL({'logger': FakeLogger()})
        downloader = HlsFD(ydl, {})
        info_dict = {
            'url': 'http://127.0.0.1:%d/%s_out.m3u8' % (self.port, self._testMethodName),
            'ext': 'mp4'
        }
        r = downloader.real_download(os.path.join(DATA_DIR, '%s_destination.mp4' % self._testMethodName), info_dict)
        self.assertTrue(r)


if __name__ == '__main__':
    unittest.main()
