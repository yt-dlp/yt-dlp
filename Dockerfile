FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        aria2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY telegram_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_bot/ /app/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /downloads /data

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "bot.py"]
