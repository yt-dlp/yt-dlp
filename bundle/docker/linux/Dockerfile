ARG BASEIMAGE=ghcr.io/yt-dlp/manylinux2014_x86_64-shared:latest

FROM $BASEIMAGE AS base

WORKDIR /yt-dlp
COPY build.sh /build.sh
ENTRYPOINT ["/build.sh"]
