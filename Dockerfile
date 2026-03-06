FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Создаём непривилегированного пользователя (UID/GID 1000)
# Перед первым запуском убедитесь, что host-директории доступны:
#   mkdir -p data/downloads data/db && chown -R 1000:1000 data/
RUN groupadd --gid 1000 botuser \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /sbin/nologin botuser

WORKDIR /app

COPY telegram_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_bot/ /app/

# Создаём точки монтирования с правильным владельцем
RUN mkdir -p /downloads /data \
    && chown -R botuser:botuser /app /downloads /data

USER botuser

CMD ["python", "bot.py"]
