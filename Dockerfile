# Hostinger: runs hostinger_server.py on Aura. ffmpeg merges video and audio; deno solves YouTube's player JavaScript.
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home app

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir '.[default,deno]'

USER app
ENV PORT=8000
EXPOSE 8000
CMD ["python", "hostinger_server.py"]
