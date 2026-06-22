"""Provider-agnostic extraction: build ydl_opts from extract_type and call yt-dlp."""

from __future__ import annotations

import os
import sys
from typing import Literal
from urllib.parse import urlparse

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


# ---------------------------------------------------------------------------
# HTTP byte-counting instrumentation
# ---------------------------------------------------------------------------

def _url_label(url: str) -> str:
    """Return scheme+host+path of a URL, dropping query params and tokens."""
    try:
        p = urlparse(url)
        return f'{p.scheme}://{p.netloc}{p.path}'
    except Exception:
        return url[:80]


class _CountingResponse:
    """Transparent proxy for a yt-dlp Response that counts bytes via read()."""

    def __init__(self, inner, entry: dict):
        self._inner = inner
        self._entry = entry  # {'url': str, 'bytes': int}

    def read(self, amt=None):
        data = self._inner.read(amt)
        if data:
            self._entry['bytes'] += len(data)
        return data

    def readable(self):
        return self._inner.readable()

    def close(self):
        return self._inner.close()

    @property
    def closed(self):
        return self._inner.closed

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class _MeasuringYoutubeDL(YoutubeDL):
    """YoutubeDL subclass that records bytes read from every HTTP response."""

    def __init__(self, params):
        self.request_log: list[dict] = []  # [{'url': str, 'bytes': int}]
        super().__init__(params)

    @property
    def total_bytes(self) -> int:
        return sum(r['bytes'] for r in self.request_log)

    def urlopen(self, req):
        resp = super().urlopen(req)
        url = resp.url if hasattr(resp, 'url') else (req if isinstance(req, str) else getattr(req, 'url', '?'))
        entry = {'url': _url_label(url), 'bytes': 0}
        self.request_log.append(entry)
        return _CountingResponse(resp, entry)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

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
    if extract_type == 'video':
        # Skip the 1.2 MB /watch webpage. android_vr has REQUIRE_JS_PLAYER=False
        # and _download_ytcfg returns {} immediately (no extra HTTP call), so it
        # calls /player directly. The /next API fallback then supplies engagement
        # data (like_count, comment_count, game panel, etc.). Together ~430 KB vs
        # ~1.25 MB for the webpage path — ~66% savings with no field loss.
        base['extractor_args'] = {
            'youtube': {
                'player_client': ['android_vr'],
                'player_skip': ['webpage'],
            },
        }
    proxy = _proxy_url()
    if proxy:
        base['proxy'] = proxy
    if 'tiktok.com' in url:
        tiktok_args = _tiktok_extractor_args()
        if tiktok_args:
            base['extractor_args'] = {**(base.get('extractor_args') or {}), **tiktok_args}
    return base


def _debug_enabled() -> bool:
    return os.environ.get('DEBUG', '').strip().lower() in ('1', 'true', 'yes')


def _log_request_summary(label: str, request_log: list[dict]) -> None:
    total = sum(r['bytes'] for r in request_log)
    sys.stderr.write(
        f'METRICS [{label}]: {len(request_log)} requests, '
        f'{total:,} bytes decompressed\n'
    )
    for r in request_log:
        sys.stderr.write(f'  {r["bytes"]:>10,}B  {r["url"]}\n')


def extract(url: str, extract_type: EXTRACT_TYPES, limit: int | None = None) -> tuple[dict | None, list[dict]]:
    """
    Extract metadata for the given URL. Returns (info_dict, request_log).

    When DEBUG=true, uses _MeasuringYoutubeDL to record per-request byte counts
    and logs a summary to stderr. In production (DEBUG unset) the standard
    YoutubeDL is used and request_log is always empty.

    `limit` caps entries for playlist_flat extraction.
    """
    opts = _opts_for(extract_type, url, limit)
    debug = _debug_enabled()
    ydl_class = _MeasuringYoutubeDL if debug else YoutubeDL
    with ydl_class(opts) as ydl:
        result = ydl.extract_info(url, download=False)
        request_log = list(ydl.request_log) if debug else []

    if debug:
        _log_request_summary(extract_type, request_log)

    if result is None:
        return None, request_log
    # remove_private_keys=True would strip 'entries' from playlists; keep it so channel/videos returns the list
    return YoutubeDL.sanitize_info(result, remove_private_keys=False), request_log
