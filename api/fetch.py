from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from api.common import extract_media, is_http_url, safe_filename


def _read_args(path):
    query = parse_qs(urlparse(path).query)
    url = (query.get('url') or [''])[0].strip()
    fmt = (query.get('format') or ['best'])[0].strip() or 'best'
    audio_only = ((query.get('audio_only') or ['false'])[0].lower() == 'true')
    single_video = ((query.get('single_video') or ['true'])[0].lower() != 'false')
    return url, fmt, audio_only, single_video


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url, fmt, audio_only, single_video = _read_args(self.path)

        if not url or not is_http_url(url):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid or missing url parameter')
            return

        try:
            media = extract_media(url, fmt=fmt, audio_only=audio_only, single_video=single_video)
            stream_url = media.get('stream_url')
            if not stream_url:
                self.send_response(422)
                self.end_headers()
                self.wfile.write(b'Could not resolve direct media URL')
                return

            req_headers = media.get('http_headers') or {}
            req = Request(stream_url, headers=req_headers)
            with urlopen(req, timeout=25) as upstream:
                ext = media.get('ext') or 'mp4'
                filename = f"{safe_filename(media.get('title') or media.get('id') or 'video')}.{ext}"
                self.send_response(200)
                self.send_header('Content-Type', upstream.headers.get('Content-Type', 'application/octet-stream'))
                self.send_header('Content-Disposition', f"attachment; filename*=UTF-8''{quote(filename)}")
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()

                while True:
                    chunk = upstream.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except HTTPError as exc:
            self.send_response(exc.code or 502)
            self.end_headers()
            self.wfile.write(f'Upstream media server error: HTTP {exc.code}'.encode('utf-8'))
        except URLError as exc:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f'Could not connect to upstream media server: {exc.reason}'.encode('utf-8'))
        except Exception as exc:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'Download failed: {exc}'.encode('utf-8'))
