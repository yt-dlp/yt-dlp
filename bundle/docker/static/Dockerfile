FROM alpine:3.19 as base

RUN apk --update add --no-cache \
        build-base \
        python3 \
        pipx \
    ;

RUN pipx install pyinstaller
# Requires above step to prepare the shared venv
RUN ~/.local/share/pipx/shared/bin/python -m pip install -U wheel
RUN apk --update add --no-cache \
        scons \
        patchelf \
        binutils \
    ;
RUN pipx install staticx

WORKDIR /yt-dlp
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT /entrypoint.sh
