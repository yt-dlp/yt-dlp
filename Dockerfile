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

# ── Устанавливаем yt-dlp из локального исходного кода ──────────────────────
# При синхронизации master с upstream yt-dlp, сборка получит актуальную версию.
# Копируем только файлы, нужные для pip install (pyproject.toml + yt_dlp/)
COPY pyproject.toml README.md LICENSE /build/
COPY yt_dlp/ /build/yt_dlp/
RUN pip install --no-cache-dir /build && rm -rf /build

# ── Устанавливаем зависимости бота ─────────────────────────────────────────
COPY telegram_bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Копируем код бота ──────────────────────────────────────────────────────
COPY telegram_bot/ /app/

# ── Версия: записываем git commit в файл ───────────────────────────────────
# Передаётся автоматически через deploy.sh (рекомендуется).
# Fallback: RELEASE_GIT_HEAD из yt_dlp/version.py.
ARG GIT_COMMIT=
RUN if [ -n "${GIT_COMMIT}" ]; then \
      echo "${GIT_COMMIT}" > /app/.git_commit; \
    else \
      python -c "from yt_dlp.version import RELEASE_GIT_HEAD; print(RELEASE_GIT_HEAD[:7])" > /app/.git_commit 2>/dev/null || echo "dev" > /app/.git_commit; \
    fi

RUN chmod +x /app/entrypoint.sh \
    # Папки создаются заранее; entrypoint исправляет владельца после монтирования томов
    && mkdir -p /downloads /data \
    && chown botuser:botuser /app /downloads /data

# НЕ ставим USER botuser здесь — entrypoint запускается от root,
# исправляет chown на смонтированных томах, затем exec gosu понижает до botuser.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "bot.py"]
