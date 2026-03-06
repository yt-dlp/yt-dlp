FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cache layer)
COPY telegram_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install yt-dlp from the local repo (so you always use the latest code)
COPY pyproject.toml /app/pyproject.toml
COPY yt_dlp/ /app/yt_dlp/
RUN pip install --no-cache-dir -e .

# Copy the bot source
COPY telegram_bot/ /app/

# Runtime directories (will be mounted as volumes in production)
RUN mkdir -p /downloads /data

# Non-root user for security
RUN useradd -r -u 1001 botuser \
    && chown -R botuser:botuser /app /downloads /data
USER botuser

CMD ["python", "bot.py"]
