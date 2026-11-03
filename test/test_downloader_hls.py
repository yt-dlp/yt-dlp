#!/usr/bin/env python3
import contextlib
import http.server
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp import YoutubeDL
from yt_dlp.utils._utils import _YDLLogger


class HLSTestRequestHandler(http.server.BaseHTTPRequestHandler):
    MANIFEST = b'#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:1,\nsubtitle.vtt\n#EXT-X-ENDLIST\n'
    SUBTITLE = b'WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello\n'

    def log_message(self, *args):
        pass

    def do_GET(self):
        content = {'/playlist.m3u8': self.MANIFEST, '/subtitle.vtt': self.SUBTITLE}.get(self.path)
        if content is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)


class TestHlsFD(unittest.TestCase):
    def test_write_pages_subtitles(self):
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), HLSTestRequestHandler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for write_pages, video_id in ((False, None), (True, None), (True, 'video-id')):
                    with self.subTest(write_pages=write_pages, video_id=video_id), tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
                        info = {
                            'url': f'http://127.0.0.1:{server.server_port}/playlist.m3u8',
                            'ext': 'vtt', 'protocol': 'm3u8_native',
                        }
                        if video_id is not None:
                            info['id'] = video_id
                        with YoutubeDL({'write_pages': write_pages, 'logger': _YDLLogger()}) as ydl:
                            ydl.dl('output.vtt', info, subtitle=True)
                        self.assertIn('Hello', Path('output.vtt').read_text())
                        dumps = list(Path('.').glob('*.dump'))
                        self.assertEqual(len(dumps), int(write_pages))
                        if write_pages:
                            self.assertEqual(dumps[0].read_bytes(), HLSTestRequestHandler.MANIFEST)
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    unittest.main()
