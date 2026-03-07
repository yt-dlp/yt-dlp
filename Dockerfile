FROM python:3.12-slim

# Устанавливаем системные зависимости + gosu для безопасного снижения привилегий
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        aria2 \
        gosu \
    && rm -rf /var/lib/apt/lists/* \
    # Создаём пользователя botuser с фиксированным UID/GID=1000.
    # Фиксированный UID важен: владелец примонтированных папок на хосте
    # должен совпадать с UID внутри контейнера.
    && groupadd --gid 1000 botuser \
    && useradd  --uid 1000 --gid 1000 --no-create-home --shell /bin/false botuser

WORKDIR /app

COPY telegram_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_bot/ /app/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    # Папки создаются заранее; entrypoint исправляет владельца после монтирования томов
    && mkdir -p /downloads /data \
    && chown botuser:botuser /app /downloads /data

# НЕ ставим USER botuser здесь — entrypoint запускается от root,
# исправляет chown на смонтированных томах, затем exec gosu понижает до botuser.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "bot.py"]
