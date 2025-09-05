#!/bin/sh
set -eu

if [ -n "${TEST_ONEDIR_BUILD:-}" ]; then
    echo "Extracting zip to verify onedir build"
    if command -v python3 >/dev/null 2>&1; then
        python3 -m zipfile -e "/build/${EXE_NAME}.zip" ./
    else
        echo "Attempting to install unzip"
        if command -v dnf >/dev/null 2>&1; then
            dnf -y install --allowerasing unzip
        elif command -v yum >/dev/null 2>&1; then
            yum -y install unzip
        elif command -v apt-get >/dev/null 2>&1; then
            DEBIAN_FRONTEND=noninteractive apt-get update -qq
            DEBIAN_FRONTEND=noninteractive apt-get install -qq -y --no-install-recommends unzip
        elif command -v apk >/dev/null 2>&1; then
            apk add --no-cache unzip
        else
            echo "Unsupported image"
            exit 1
        fi
        unzip "/build/${EXE_NAME}.zip" -d ./
    fi
else
    echo "Verifying onefile build"
    cp "/build/${EXE_NAME}" ./
fi

chmod +x "./${EXE_NAME}"

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
