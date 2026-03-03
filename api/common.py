import re
from urllib.parse import urlparse

from yt_dlp import YoutubeDL


def is_http_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def safe_filename(name, fallback='video'):
    name = (name or fallback).strip()
    name = re.sub(r'[\\/:*?"<>|]+', '_', name)
    return name[:180] or fallback


def extract_media(url, fmt='best', audio_only=False, single_video=True):
    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': bool(single_video),
    }

    if audio_only:
        ydl_opts['format'] = 'bestaudio/best'

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if 'entries' in info and info.get('entries'):
        info = next((entry for entry in info['entries'] if entry), None) or info

    return {
        'id': info.get('id'),
        'title': info.get('title'),
        'duration': info.get('duration'),
        'webpage_url': info.get('webpage_url') or url,
        'stream_url': info.get('url'),
        'extractor': info.get('extractor_key') or info.get('extractor'),
        'ext': info.get('ext') or 'mp4',
        'http_headers': info.get('http_headers') or {},
    }
