#!/bin/sh
exec python3 "$(dirname "$(realpath "$0")")/yt_dlp/__main__.py" "$@"
