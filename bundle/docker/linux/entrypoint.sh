#!/bin/bash
set -exuo pipefail

python3 -m venv ~/yt-dlp-build-venv
source ~/yt-dlp-build-venv/bin/activate
python3 -m devscripts.install_deps -o --include build
python3 -m devscripts.install_deps --include secretstorage --include curl-cffi --include pyinstaller
python3 -m devscripts.make_lazy_extractors
python3 devscripts/update-version.py -c "${channel}" -r "${origin}" "${version}"
python3 -m bundle.pyinstaller
mv dist/* /build/
