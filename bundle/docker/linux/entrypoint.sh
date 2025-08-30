#!/bin/bash
set -exuo pipefail

: "${USE_PYTHON_VERSION:="3.13"}"

export USE_PYTHON_VERSION

function runpy {
    "/opt/shared-cpython-${USE_PYTHON_VERSION}/bin/python${USE_PYTHON_VERSION}" "$@"
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
runpy -m ensurepip --upgrade --default-pip
runpy -m devscripts.install_deps -o --include build
runpy -m devscripts.install_deps "${INCLUDES[@]}"
runpy -m devscripts.make_lazy_extractors
runpy devscripts/update-version.py -c "${CHANNEL}" -r "${ORIGIN}" "${VERSION}"

if [[ -z "${SKIP_ONEDIR_BUILD:-}" ]]; then
    runpy -m bundle.pyinstaller --onedir
    pushd "./dist/${EXE_NAME}"
    runpy -m zipfile -c "/build/${EXE_NAME}.zip" ./
    popd
fi

if [[ -z "${SKIP_ONEFILE_BUILD:-}" ]]; then
    runpy -m bundle.pyinstaller
    mv "./dist/${EXE_NAME}" /build/
fi
