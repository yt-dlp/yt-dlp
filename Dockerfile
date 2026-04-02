FROM python:3.13-slim-bookworm AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /src

COPY LICENSE README.md pyproject.toml /src/
COPY devscripts /src/devscripts
COPY yt_dlp /src/yt_dlp

RUN python -m devscripts.make_lazy_extractors \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install ".[default,curl-cffi]"


FROM python:3.13-slim-bookworm

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

COPY --from=build /opt/venv /opt/venv

ENTRYPOINT ["yt-dlp"]
CMD ["--help"]
