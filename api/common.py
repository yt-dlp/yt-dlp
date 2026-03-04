import re
import os
from urllib.parse import urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


def is_http_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def safe_filename(name, fallback='video'):
    name = (name or fallback).strip()
    name = re.sub(r'[\\/:*?"<>|]+', '_', name)
    return name[:180] or fallback


def _cookies_from_browser_value(raw):
    # Format examples:
    #   chrome
    #   firefox:default
    #   chrome:Profile 3:/home/user/.config/google-chrome
    if not raw:
        return None
    parts = [part.strip() for part in raw.split(':')]
    browser = parts[0]
    profile = parts[1] if len(parts) > 1 and parts[1] else None
    keyring = None
    container = None
    path = parts[2] if len(parts) > 2 and parts[2] else None
    if len(parts) > 3 and parts[3]:
        keyring = parts[3]
    if len(parts) > 4 and parts[4]:
        container = parts[4]
    return (browser, profile, keyring, container) if path is None else (browser, profile, keyring, container, path)


def _candidate_cookie_opts():
    cookiefile = os.getenv('YTDLP_COOKIE_FILE', '').strip()
    cookies_from_browser = os.getenv('YTDLP_COOKIES_FROM_BROWSER', '').strip()

    candidates = []
    if cookiefile:
        candidates.append({'cookiefile': cookiefile})

    parsed = _cookies_from_browser_value(cookies_from_browser)
    if parsed:
        candidates.append({'cookiesfrombrowser': parsed})

    # No explicit env: try common browser locations as a best effort for local self-hosting
    if not candidates:
        for browser in ('chrome', 'chromium', 'edge', 'brave', 'firefox'):
            candidates.append({'cookiesfrombrowser': (browser,)})

    return candidates


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

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        if 'youtube' not in (urlparse(url).netloc or '').lower():
            raise

        info = None
        last_error = exc
        for cookie_opt in _candidate_cookie_opts():
            retry_opts = {**ydl_opts, **cookie_opt}
            try:
                with YoutubeDL(retry_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                break
            except Exception as retry_exc:
                last_error = retry_exc

        if info is None:
            raise RuntimeError(
                'YouTube extraction failed. Set YTDLP_COOKIE_FILE to an exported cookies.txt '
                'or set YTDLP_COOKIES_FROM_BROWSER (e.g. chrome, firefox:default) '
                'to allow yt-dlp to reuse authenticated browser cookies. '
                f'Original error: {last_error}'
            )

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
