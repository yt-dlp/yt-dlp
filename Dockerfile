FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (yt-dlp pulled from PyPI, always latest)
COPY telegram_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot source
COPY telegram_bot/ /app/

# Runtime directories (will be mounted as volumes in production)
RUN mkdir -p /downloads /data

# Non-root user for security
RUN useradd -r -u 1001 botuser \
    && chown -R botuser:botuser /app /downloads /data
USER botuser

CMD ["python", "bot.py"]
