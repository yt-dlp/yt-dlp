#!/bin/bash
set -exuo pipefail

if [[ -z "${USE_PYTHON_VERSION:-}" ]]; then
    USE_PYTHON_VERSION="3.13"
fi

function runpy {
    "/opt/shared-cpython-${USE_PYTHON_VERSION}/bin/python${USE_PYTHON_VERSION}" "$@"
}

function venvpy {
    "python${USE_PYTHON_VERSION}" "$@"
}

INCLUDES=(
    --include pyinstaller
    --include secretstorage
)

if [[ -z "${EXCLUDE_CURL_CFFI:-}" ]]; then
    INCLUDES+=(--include curl-cffi)
fi

runpy -m venv /yt-dlp-build-venv
source /yt-dlp-build-venv/bin/activate
# Inside the venv we use venvpy instead of runpy
venvpy -m ensurepip --upgrade --default-pip
venvpy -m devscripts.install_deps -o --include build
venvpy -m devscripts.install_deps "${INCLUDES[@]}"
venvpy -m devscripts.make_lazy_extractors
venvpy devscripts/update-version.py -c "${CHANNEL}" -r "${ORIGIN}" "${VERSION}"

if [[ -z "${SKIP_ONEDIR_BUILD:-}" ]]; then
    mkdir -p /build
    venvpy -m bundle.pyinstaller --onedir --distpath=/build
    pushd "/build/${EXE_NAME}"
    chmod +x "${EXE_NAME}"
    venvpy -m zipfile -c "/yt-dlp/dist/${EXE_NAME}.zip" ./
    popd
fi

if [[ -z "${SKIP_ONEFILE_BUILD:-}" ]]; then
    venvpy -m bundle.pyinstaller
    chmod +x "./dist/${EXE_NAME}"
fi
