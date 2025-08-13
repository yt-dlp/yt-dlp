#!/bin/bash
set -exuo pipefail

function runpy {
    case ${USE_PYTHON_VERSION:-} in
        "3.11") python3.11 "$@";;
        "3.13") python3.13 "$@";;
        *)      python3 "$@";;
    esac
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

runpy -m bundle.pyinstaller
mv "./dist/${EXE_NAME}" /build/
