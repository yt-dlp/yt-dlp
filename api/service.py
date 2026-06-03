"""Provider-agnostic extraction: build ydl_opts from extract_type and call yt-dlp."""

from __future__ import annotations

import os
import sys
from typing import Literal

from yt_dlp import YoutubeDL


EXTRACT_TYPES = Literal['playlist_flat', 'video']

# Warnings that are noise for metadata-only extraction (we never download
# formats, so missing-format / JS-runtime notices don't matter). Matched as
# substrings against the warning text. Anything not listed here — e.g. HTTP 429
# rate-limiting, geo-blocks, real extraction failures — is kept.
_SUPPRESSED_WARNINGS = (
    'No supported JavaScript runtime',
    'YouTube extraction without a JS runtime has been deprecated',
    'have been skipped as they are missing a URL',  # SABR / android_vr format skips
    'SABR-only streaming experiment',
)


class _FilteringLogger:
    """yt-dlp logger that drops known-noise warnings but forwards the rest.

    Setting a `logger` in ydl_opts makes report_warning route here instead of
    honoring `no_warnings` — so we can suppress selectively rather than all or
    nothing. Output is written to stderr with yt-dlp's native prefixes so log
    scraping/grep for `WARNING:` / `ERROR:` keeps working.
    """

    def debug(self, msg: str) -> None:
        # to_screen() (the output `quiet` normally hides) and verbose [debug]
        # lines route here. Drop them — the API runs quiet.
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        if any(s in msg for s in _SUPPRESSED_WARNINGS):
            return
        sys.stderr.write(f'WARNING: {msg}\n')

    def error(self, msg: str) -> None:
        # msg already carries yt-dlp's "ERROR:" prefix from report_error.
        sys.stderr.write(f'{msg}\n')


YTDLP_LOGGER = _FilteringLogger()


def _proxy_url() -> str | None:
    """Proxy URL from PROXY_URL env, or None if unset."""
    url = os.environ.get('PROXY_URL', '').strip()
    return url or None


def _tiktok_extractor_args() -> dict | None:
    """TikTok extractor args (device_id + app_info) when TIKTOK_DEVICE_ID is set. Required for hashtag posts (mobile API)."""
    device_id = os.environ.get('TIKTOK_DEVICE_ID', '').strip()
    if not device_id:
        return None
    return {
        'tiktok': {
            'device_id': [device_id],
            'app_info': [''],  # use extractor defaults; device_id alone enables mobile API
        },
    }


def _opts_for(extract_type: EXTRACT_TYPES, url: str = '', limit: int | None = None) -> dict:
    base = {
        'skip_download': True,
        'quiet': True,
        # Route output through a logger that drops noise warnings (JS runtime,
        # skipped formats) but keeps signal like HTTP 429. See _FilteringLogger.
        'logger': YTDLP_LOGGER,
        'ignore_no_formats_error': True,
        'http_headers': {
            'Accept-Encoding': 'gzip, deflate',
        },
    }
    if extract_type == 'playlist_flat':
        base['extract_flat'] = 'in_playlist'
        # Bound playlist extraction so a huge channel can't pull thousands of
        # entries into memory (sanitize_info deep-copies the whole result, then
        # the JSON encoder copies it again — ~3x the payload at peak).
        if limit is not None and limit > 0:
            base['playlistend'] = limit
    proxy = _proxy_url()
    if proxy:
        base['proxy'] = proxy
    if 'tiktok.com' in url:
        tiktok_args = _tiktok_extractor_args()
        if tiktok_args:
            base['extractor_args'] = {**(base.get('extractor_args') or {}), **tiktok_args}
    return base


def extract(url: str, extract_type: EXTRACT_TYPES, limit: int | None = None) -> dict | None:
    """
    Extract metadata for the given URL. No provider-specific logic;
    yt-dlp selects the extractor from the URL. `limit` caps the number of
    entries for playlist_flat extraction (passed to yt-dlp as playlistend).
    """
    opts = _opts_for(extract_type, url, limit)
    with YoutubeDL(opts) as ydl:
        result = ydl.extract_info(url, download=False)
    if result is None:
        return None
    # remove_private_keys=True would strip 'entries' from playlists; keep it so channel/videos returns the list
    return YoutubeDL.sanitize_info(result, remove_private_keys=False)
