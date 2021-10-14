#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import http_server_port, is_download_test
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


@is_download_test
class TestHLS(unittest.TestCase):
    def setUp(self):
        self.httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 8000), HTTPTestRequestHandler)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        ydl = YoutubeDL({'logger': FakeLogger()})
        self.downloader = HlsFD(ydl, {})
        self.playlist = '%s_out.m3u8' % self._testMethodName

    def tearDown(self):
        self.httpd.server_close()
        self.httpd.shutdown()

    def doCleanups(self):
        try:
            os.remove('_'.join((self._testMethodName, 'destination.mp4')))
        except (FileNotFoundError, IsADirectoryError):
            pass

        for file in ['out.m3u8', 'out.ts', 'out0.ts', 'out1.ts', 'out2.ts', 'out3.ts', 'out4.ts', 'out5.ts', 'out6.ts']:
            try:
                os.remove(os.path.join(DATA_DIR, '_'.join((self._testMethodName, file))))
            except (FileNotFoundError, IsADirectoryError):
                pass

    def test_real_download_byterange(self):
        was_error = False
        try:
            handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=0.65',
                                       '-hls_init_time', '0.1s', '-hls_flags', 'split_by_time+single_file',
                                       self.playlist],
                                      cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.fail("Error occurred during generating files.")

        info_dict = {
            'url': 'http://127.0.0.1:%d/%s' % ((http_server_port(self.httpd)), playlist),
            'ext': 'mp4'
        }
        r = self.downloader.real_download('%s_destination.mp4' % self._testMethodName, info_dict)
        self.assertTrue(r)

    @unittest.skip("Broken test data, see also: https://trac.ffmpeg.org/ticket/8783")
    def test_real_download_byterange_iv(self):
        key_info_filename = 'file_iv.keyinfo'

        was_error = False
        try:
            handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=0.65',
                                       '-hls_init_time', '0.1s', '-hls_flags', 'split_by_time+single_file',
                                       '-hls_key_info_file', key_info_filename, self.playlist],
                                      cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.fail("Error occurred during generating files.")

        info_dict = {
            'url': 'http://127.0.0.1:%d/%s' % ((http_server_port(self.httpd)), playlist),
            'ext': 'mp4'
        }
        r = self.downloader.real_download('%s_destination.mp4' % self._testMethodName, info_dict)
        self.assertTrue(r)

    def test_real_download_noiv(self):
        key_info_filename = 'file_noiv.keyinfo'

        was_error = False
        try:
            handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=0.65',
                                       '-hls_init_time', '0.1s', '-hls_flags', 'split_by_time',
                                       '-hls_key_info_file', key_info_filename, self.playlist],
                                      cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.fail("Error occurred during generating files.")

        info_dict = {
            'url': 'http://127.0.0.1:%d/%s' % ((http_server_port(self.httpd)), playlist),
            'ext': 'mp4'
        }
        r = self.downloader.real_download('%s_destination.mp4' % self._testMethodName, info_dict)
        self.assertTrue(r)

    def test_real_download_iv(self):
        key_info_filename = 'file_iv.keyinfo'

        was_error = False
        try:
            handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=0.65',
                                       '-hls_init_time', '0.1s', '-hls_flags', 'split_by_time',
                                       '-hls_key_info_file', key_info_filename, self.playlist],
                                      cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.fail("Error occurred during generating files.")

        info_dict = {
            'url': 'http://127.0.0.1:%d/%s' % ((http_server_port(self.httpd)), self.playlist),
            'ext': 'mp4'
        }
        r = self.downloader.real_download(self.destination, info_dict)
        self.assertTrue(r)

    def test_real_download_webvtt(self):
        video = '%s_out.m3u8' % self._testMethodName

        was_error = False
        try:
            handle = subprocess.Popen(['ffmpeg', '-n', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=0.65',
                                       '-i', 'sub.vtt', '-c:s', 'webvtt', '-metadata:s:s:1', 'language=des',
                                       '-hls_init_time', '0.1s', '-hls_flags', 'split_by_time+single_file',
                                       self.playlist],
                                      cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.fail("Error occurred during generating files.")

        info_dict = {
            'url': 'http://127.0.0.1:%d/%s_out_vtt.m3u8' % ((http_server_port(self.httpd)), self._testMethodName),
            'ext': 'vtt'
        }
        r = self.downloader.real_download(self.destination, info_dict)
        self.assertTrue(r)


if __name__ == '__main__':
    unittest.main()
