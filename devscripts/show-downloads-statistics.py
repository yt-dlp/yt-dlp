# Unused

#!/usr/bin/env python
from __future__ import unicode_literals

import itertools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.compat import (
    compat_print,
    compat_urllib_request,
)
from yt_dlp.utils import format_bytes


def format_size(bytes):
    return '%s (%d bytes)' % (format_bytes(bytes), bytes)


total_bytes = 0

for page in itertools.count(1):
    releases = json.loads(compat_urllib_request.urlopen(
        'https://api.github.com/repos/ytdl-org/youtube-dl/releases?page=%s' % page
    ).read().decode('utf-8'))

    if not releases:
        break

    for release in releases:
        compat_print(release['name'])
        for asset in release['assets']:
            asset_name = asset['name']
            total_bytes += asset['download_count'] * asset['size']
            if all(not re.match(p, asset_name) for p in (
                    r'^yt-dlp$',
                    r'^yt-dlp-\d{4}\.\d{2}\.\d{2}(?:\.\d+)?\.tar\.gz$',
                    r'^yt-dlp\.exe$')):
                continue
            compat_print(
                ' %s size: %s downloads: %d'
                % (asset_name, format_size(asset['size']), asset['download_count']))

compat_print('total downloads traffic: %s' % format_size(total_bytes))
