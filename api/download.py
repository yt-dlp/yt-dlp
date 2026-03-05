from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse

from api.common import extract_media, is_http_url


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        self._handle(query)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', '0') or 0)
        raw = self.rfile.read(content_length) if content_length else b'{}'
        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return self._send_json(400, {'error': 'Invalid JSON body'})

        query = {key: [str(value)] for key, value in payload.items()}
        self._handle(query)

    def _handle(self, query):
        url = (query.get('url') or [''])[0].strip()
        fmt = (query.get('format') or ['best'])[0].strip() or 'best'
        audio_only = ((query.get('audio_only') or ['false'])[0].lower() == 'true')
        single_video = ((query.get('single_video') or ['true'])[0].lower() != 'false')

        if not url or not is_http_url(url):
            return self._send_json(400, {'error': "Query/body field 'url' must be a valid http/https URL"})

        try:
            result = extract_media(url, fmt=fmt, audio_only=audio_only, single_video=single_video)
            if not result.get('stream_url'):
                return self._send_json(422, {'error': 'Could not resolve direct media URL for this input'})
            return self._send_json(200, result)
        except Exception as exc:
            return self._send_json(500, {'error': str(exc)})
