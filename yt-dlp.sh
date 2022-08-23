#!/usr/bin/env sh
set -eu

exec "${PYTHON:-python3}" -bb -Werror -Xdev "$(dirname "$(realpath "$0")")/yt_dlp/__main__.py" "$@"
