#!/bin/sh
set -exuo

chmod +x /build/${EXE_NAME}

if [ -n "${SKIP_UPDATE_TO:-}" ]; then
    /build/${EXE_NAME} -v || true
    /build/${EXE_NAME} --version

    # TEMPORARY:
    /build/${EXE_NAME} -v --print-traffic -o- --impersonate chrome "https://tls.browserleaks.com/json" | cat

    exit 0
fi

cp /build/${EXE_NAME} ./${EXE_NAME}_downgraded
version="$(/build/${EXE_NAME} --version)"
./${EXE_NAME}_downgraded -v --update-to yt-dlp/yt-dlp@2023.03.04
downgraded_version="$(./${EXE_NAME}_downgraded --version)"
if [ "${version}" = "${downgraded_version}" ]; then
    exit 1
fi
