#!/usr/bin/env python3
import os
import subprocess
import sys
import threading
import unittest

from test.helper import http_server_port
from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_http_server
from yt_dlp.downloader import HlsFD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    def setUp(self) -> None:
        self.httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), HTTPTestRequestHandler)
        self.port = http_server_port(self.httpd)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def doCleanups(self):
        for file in ['destination.mp4', 'file.keyinfo',
                     'out.m3u8', 'out0.ts', 'out1.ts', 'out2.ts', 'out3.ts', 'out4.ts', 'out6.ts']:
            try:
                os.remove(os.path.join(DATA_DIR, file))
            except (FileNotFoundError, IsADirectoryError):
                pass

    def test_real_download_noiv(self):
        key_filename = 'file.key'
        was_error = False
        try:
            with open(os.path.join(DATA_DIR, 'file.keyinfo'), 'w') as f:
                f.write('http://127.0.0.1:%d/%s\n' % (self.port, key_filename))
                f.write(key_filename + '\n')

                handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=65',
                                           '-hls_key_info_file', 'file.keyinfo', 'out.m3u8'],
                                          cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.skipTest("Error occurred during generating files.")

        ydl = YoutubeDL({'logger': FakeLogger()})
        downloader = HlsFD(ydl, {})
        info_dict = {
            'url': 'http://127.0.0.1:%d/out.m3u8' % self.port,
            'ext': 'mp4'
        }
        r = downloader.real_download(os.path.join(DATA_DIR, 'destination.mp4'), info_dict)
        self.assertTrue(r)

    def test_real_download_iv(self):
        key_filename = 'file.key'
        was_error = False
        try:
            with open(os.path.join(DATA_DIR, 'file.keyinfo'), 'w') as f:
                f.write('http://127.0.0.1:%d/%s\n' % (self.port, key_filename))
                f.write(key_filename + '\n')

                handle = subprocess.Popen(['ffmpeg', '-f', 'lavfi', '-re', '-i', 'testsrc=duration=65',
                                           '-hls_key_info_file', 'file.keyinfo', 'out.m3u8'],
                                          cwd=DATA_DIR)
        except OSError:
            was_error = True
        if was_error or handle.wait() != 0:
            self.skipTest("Error occurred during generating files.")

        ydl = YoutubeDL({'logger': FakeLogger()})
        downloader = HlsFD(ydl, {})
        info_dict = {
            'url': 'http://127.0.0.1:%d/out.m3u8' % self.port,
            'ext': 'mp4'
        }
        r = downloader.real_download(os.path.join(DATA_DIR, 'destination.mp4'), info_dict)
        self.assertTrue(r)


if __name__ == '__main__':
    unittest.main()
