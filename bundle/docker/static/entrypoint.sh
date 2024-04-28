#!/bin/ash
set -e

source ~/.local/share/pipx/venvs/pyinstaller/bin/activate
python -m devscripts.install_deps --include secretstorage
python -m devscripts.make_lazy_extractors
python devscripts/update-version.py -c "${channel}" -r "${origin}" "${version}"
python -m bundle.pyinstaller --name yt-dlp_static
deactivate

source ~/.local/share/pipx/venvs/staticx/bin/activate
staticx /yt-dlp/dist/yt-dlp_static /build/yt-dlp_static
deactivate
chmod +rx /build/yt-dlp_static
