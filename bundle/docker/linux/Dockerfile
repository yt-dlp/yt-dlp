ARG BASEIMAGE=ghcr.io/bashonly/manylinux2014_x86_64_builds:latest

FROM $BASEIMAGE AS base

WORKDIR /yt-dlp
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT /entrypoint.sh
