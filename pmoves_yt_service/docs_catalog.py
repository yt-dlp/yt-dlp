"""Structured yt-dlp option and extractor catalog helpers for PMOVES.YT."""

from __future__ import annotations

import optparse
from functools import lru_cache
from typing import Any

import yt_dlp
from yt_dlp.extractor import list_extractors
from yt_dlp.options import create_parser
from yt_dlp.version import __version__ as YT_DLP_VERSION


def _json_safe(value: Any) -> Any:
    """Convert optparse defaults into JSON-safe values."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return str(value)


@lru_cache(maxsize=1)
def version_info() -> dict[str, Any]:
    version = getattr(yt_dlp, '__version__', None) or YT_DLP_VERSION or 'unknown'
    return {'yt_dlp_version': version}


@lru_cache(maxsize=1)
def extractor_count() -> int:
    return len(list_extractors())


@lru_cache(maxsize=1)
def options_catalog() -> dict[str, Any]:
    parser = create_parser()
    options: list[dict[str, Any]] = []
    group_count = 0

    for group in parser.option_groups:
        group_count += 1
        group_name = getattr(group, 'title', None) or 'Options'
        for option in getattr(group, 'option_list', []):
            flags = [*getattr(option, '_short_opts', []), *getattr(option, '_long_opts', [])]
            if not flags:
                continue
            if option.help in (None, optparse.SUPPRESS_HELP):
                continue
            options.append(
                {
                    'group': group_name,
                    'flags': flags,
                    'dest': option.dest,
                    'help': str(option.help).strip(),
                    'default': _json_safe(option.default),
                    'choices': _json_safe(getattr(option, 'choices', None)),
                    'metavar': getattr(option, 'metavar', None),
                    'action': getattr(option, 'action', None),
                },
            )

    return {
        'options': options,
        'counts': {
            'options': len(options),
            'groups': group_count,
        },
    }
