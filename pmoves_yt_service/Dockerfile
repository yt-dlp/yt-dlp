# Base image pinned 2026-03-05 — refresh monthly or via Dependabot
FROM python:3.11-slim@sha256:d6e4d224f70f9e0172a06a3a2eba2f768eb146811a349278b38fff3a36463b47
WORKDIR /opt/pmoves-yt
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/pmoves-yt
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg atomicparsley ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY . /opt/pmoves-yt
# Parameterize yt-dlp so operators can still override the packaged fork when needed.
ARG YTDLP_VERSION=
ARG YTDLP_PIP_URL=
RUN pip install --no-cache-dir --upgrade pip \
    "setuptools==82.0.0" "wheel==0.46.3" \
    && pip install --no-cache-dir -r pmoves_yt_service/requirements.lock \
    && if [ -n "$YTDLP_PIP_URL" ]; then pip install --no-cache-dir "$YTDLP_PIP_URL"; \
       elif [ -n "$YTDLP_VERSION" ]; then pip install --no-cache-dir "yt-dlp[default]==${YTDLP_VERSION}"; \
       else pip install --no-cache-dir ".[default]"; fi

# Security: Run as non-root user
RUN groupadd -r pmoves --gid=65532 && \
    useradd -r -g pmoves --uid=65532 --home-dir=/app --shell=/sbin/nologin pmoves && \
    mkdir -p /app/config && \
    chown -R pmoves:pmoves /app /opt/pmoves-yt

USER pmoves:pmoves
WORKDIR /app

EXPOSE 8077
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8077/healthz', timeout=4).read()" || exit 1
CMD ["uvicorn","pmoves_yt_service.yt:app","--host","0.0.0.0","--port","8077"]
