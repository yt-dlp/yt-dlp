#!/bin/bash
python3 "$(dirname $(realpath $0))/yt_dlp/__main__.py" "$@"
