"""Hostinger: an HTTP endpoint that downloads one YouTube video as a small MP4 for the reporter's video reviews.

GET /download?videoId=<11 chars>  with  Authorization: Bearer <DOWNLOADER_TOKEN>
    -> 200 video/mp4 (360p, original audio). Unlisted videos work; private ones do not.
GET /health -> 200 "ok"
"""
import hmac
import os
import re
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import yt_dlp

TOKEN = os.environ['DOWNLOADER_TOKEN']
PORT = int(os.environ.get('PORT', '8000'))
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
# ponytail: one download at a time; a queue or workers if previews ever arrive in bulk
DOWNLOAD_LOCK = threading.Lock()


def download(video_id: str, directory: str) -> str:
    options = {
        # 360p H.264 is enough for a review. yt-dlp ranks the original audio track above auto-dubbed ones.
        'format': 'bv*[height<=360][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=360][ext=mp4]+ba[ext=m4a]/b[height<=360]/bv*+ba/b',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(directory, 'video.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'max_filesize': 2 * 1024 ** 3,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=True)
        return info['requested_downloads'][0]['filepath']


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/health':
            return self.reply(200, 'ok')
        if url.path != '/download':
            return self.reply(404, 'Not found')
        if not hmac.compare_digest(self.headers.get('Authorization', ''), f'Bearer {TOKEN}'):
            return self.reply(401, 'Unauthorized')
        video_id = parse_qs(url.query).get('videoId', [''])[0]
        if not VIDEO_ID.match(video_id):
            return self.reply(400, 'videoId must be an 11-character YouTube video ID')

        directory = tempfile.mkdtemp(prefix='preview-')
        try:
            with DOWNLOAD_LOCK:
                path = download(video_id, directory)
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(os.path.getsize(path)))
            self.end_headers()
            with open(path, 'rb') as file:
                shutil.copyfileobj(file, self.wfile)
        except yt_dlp.utils.DownloadError as error:
            # YouTube's reason, for example "Private video" or "Sign in to confirm you're not a bot".
            self.reply(502, str(error))
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def reply(self, status: int, text: str):
        body = text.encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
