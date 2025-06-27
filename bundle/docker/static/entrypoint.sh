#!/bin/ash
set -e

source ~/.local/share/pipx/venvs/pyinstaller/bin/activate
python -m devscripts.install_deps -o --include build
python -m devscripts.install_deps --include secretstorage --include curl-cffi
python -m devscripts.make_lazy_extractors
python devscripts/update-version.py -c "${channel}" -r "${origin}" "${version}"
python -m bundle.pyinstaller
deactivate

source ~/.local/share/pipx/venvs/staticx/bin/activate
staticx /yt-dlp/dist/yt-dlp_linux /build/yt-dlp_linux
deactivate
