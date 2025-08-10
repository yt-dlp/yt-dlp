#!/bin/bash
set -e

python3.13 -m venv ~/yt-dlp-build-venv
source ~/yt-dlp-build-venv/bin/activate
python3.13 -m devscripts.install_deps -o --include build
python3.13 -m devscripts.install_deps --include secretstorage --include curl-cffi --include pyinstaller
python3.13 -m devscripts.make_lazy_extractors
python3.13 devscripts/update-version.py -c "${channel}" -r "${origin}" "${version}"
python3.13 -m bundle.pyinstaller
mv dist/* /build/
