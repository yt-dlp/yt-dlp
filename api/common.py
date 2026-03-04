import os
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
    # Supported values:
    #   chrome
    #   firefox:default
    #   chrome:Profile 3:/home/user/.config/google-chrome
    if not raw:
        return None
    parts = [part.strip() for part in raw.split(':') if part.strip()]
    if not parts:
        return None
    if len(parts) == 1:
        return (parts[0],)
    if len(parts) == 2:
        return (parts[0], parts[1])
    return tuple(parts)


def _configured_cookie_opts():
    cookiefile = os.getenv('YTDLP_COOKIE_FILE', '').strip()
    cookies_from_browser = os.getenv('YTDLP_COOKIES_FROM_BROWSER', '').strip()

    opts = []
    if cookiefile:
        opts.append({'cookiefile': cookiefile})

    parsed = _cookies_from_browser_value(cookies_from_browser)
    if parsed:
        opts.append({'cookiesfrombrowser': parsed})

    return opts


def _youtube_extractor_args():
    # Try clients that are usually more resilient for public videos
    return {
        'youtube': {
            'player_client': ['android', 'web'],
            'player_skip': ['configs'],
        }
    }


def _base_ydl_opts(fmt, audio_only, single_video):
    resolved_format = 'bestaudio/best' if audio_only else fmt
    return {
        'format': resolved_format,
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': bool(single_video),
        'extractor_args': _youtube_extractor_args(),
    }


def extract_media(url, fmt='best', audio_only=False, single_video=True):
    ydl_opts = _base_ydl_opts(fmt, audio_only, single_video)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        if 'youtube' not in (urlparse(url).netloc or '').lower():
            raise

        info = None
        last_error = exc
        cookie_opts = _configured_cookie_opts()

        for cookie_opt in cookie_opts:
            retry_opts = {**ydl_opts, **cookie_opt}
            try:
                with YoutubeDL(retry_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                break
            except Exception as retry_exc:
                last_error = retry_exc

        if info is None:
            if cookie_opts:
                raise RuntimeError(
                    'YouTube extraction failed even with configured cookies. '
                    'Please refresh/export cookies and try again. '
                    f'Original error: {last_error}'
                )
            raise RuntimeError(
                'YouTube may require authenticated cookies for this request. '
                'Set YTDLP_COOKIE_FILE to an exported cookies.txt, or set '
                'YTDLP_COOKIES_FROM_BROWSER (e.g. chrome or firefox:default), '
                'then retry.'
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
