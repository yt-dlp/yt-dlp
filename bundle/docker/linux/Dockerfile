ARG BUILDIMAGE=ghcr.io/yt-dlp/manylinux2014_x86_64-shared:latest
ARG VERIFYIMAGE=alpine:3.22


FROM $BUILDIMAGE AS build

WORKDIR /yt-dlp
COPY build.sh /build.sh
ENTRYPOINT ["/build.sh"]


FROM $VERIFYIMAGE AS verify

WORKDIR /testing
COPY verify.sh /verify.sh
ENTRYPOINT ["/verify.sh"]
