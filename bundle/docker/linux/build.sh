#!/bin/bash
set -exuo pipefail

if [[ -z "${PYTHON_VERSION:-}" ]]; then
    PYTHON_VERSION="3.13"
    echo "Defaulting to using Python ${PYTHON_VERSION}"
fi

INCLUDES=(
    --include-extra pyinstaller
    --include-extra secretstorage
)

if [[ -z "${EXCLUDE_CURL_CFFI:-}" ]]; then
    INCLUDES+=(--include-extra build-curl-cffi)
fi

py"${PYTHON_VERSION}" -m venv /yt-dlp-build-venv
# shellcheck disable=SC1091
source /yt-dlp-build-venv/bin/activate
# Inside the venv we can use python instead of py3.13 or py3.14 etc
python -m devscripts.install_deps "${INCLUDES[@]}"
python -m devscripts.make_lazy_extractors
python devscripts/update-version.py -c "${CHANNEL}" -r "${ORIGIN}" "${VERSION}"

if [[ -z "${SKIP_ONEDIR_BUILD:-}" ]]; then
    mkdir -p /build
    python -m bundle.pyinstaller --onedir --distpath=/build
    pushd "/build/${EXE_NAME}"
    chmod +x "${EXE_NAME}"
    python -m zipfile -c "/yt-dlp/dist/${EXE_NAME}.zip" ./
    popd
fi

if [[ -z "${SKIP_ONEFILE_BUILD:-}" ]]; then
    python -m bundle.pyinstaller
    chmod +x "./dist/${EXE_NAME}"
fi

deactivate
