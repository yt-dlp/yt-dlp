ARG BASEIMAGE=ghcr.io/yt-dlp/manylinux2014_x86_64-shared:latest

FROM $BASEIMAGE AS base

WORKDIR /yt-dlp
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT /entrypoint.sh
