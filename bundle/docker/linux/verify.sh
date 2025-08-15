#!/bin/sh
set -eu

if [ -n "${TEST_ONEDIR_BUILD:-}" ]; then
    echo "Extracting zip to verify onedir build"
    "${PYTHON:-python}" -m zipfile -e "/build/${EXE_NAME}.zip" ./
else
    echo "Verifying onefile build"
    cp "/build/${EXENAME}" ./
fi

chmod +x "./${EXE_NAME}"

if [ -z "${EXCLUDE_CURL_CFFI:-}" ]; then
    "./${EXE_NAME}" -v --print-traffic --impersonate chrome "https://tls.browserleaks.com/json" -o ./resp.json
    cat ./resp.json
fi

if [ -n "${SKIP_UPDATE_TO:-}" ] || [ -n "${TEST_ONEDIR_BUILD:-}" ]; then
    "./${EXE_NAME}" -v || true
    "./${EXE_NAME}" --version
    exit 0
fi

cp "./${EXE_NAME}" "./${EXE_NAME}_downgraded"
version="$("./${EXE_NAME}" --version)"
"./${EXE_NAME}_downgraded" -v --update-to yt-dlp/yt-dlp@2023.03.04
downgraded_version="$("./${EXE_NAME}_downgraded" --version)"
if [ "${version}" = "${downgraded_version}" ]; then
    exit 1
fi
