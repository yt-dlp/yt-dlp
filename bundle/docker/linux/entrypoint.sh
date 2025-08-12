#!/bin/bash
set -exuo pipefail

python3 -m venv ~/yt-dlp-build-venv
source ~/yt-dlp-build-venv/bin/activate
python3 -m devscripts.install_deps -o --include build
python3 -m devscripts.install_deps --include secretstorage --include curl-cffi --include pyinstaller
python3 -m devscripts.make_lazy_extractors
python3 devscripts/update-version.py -c "${CHANNEL}" -r "${ORIGIN}" "${VERSION}"
python3 -m bundle.pyinstaller --onedir
pushd "./dist/${EXE_NAME}"
python3 -m zipfile -c "/build/${EXE_NAME}.zip" ./
popd
python3 -m bundle.pyinstaller
mv "./dist/${EXE_NAME}" /build/
