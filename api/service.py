"""Provider-agnostic extraction: build ydl_opts from extract_type and call yt-dlp."""

from __future__ import annotations

import os
from typing import Literal

from yt_dlp import YoutubeDL


EXTRACT_TYPES = Literal['playlist_flat', 'video']


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
