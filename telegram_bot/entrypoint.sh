#!/bin/sh
set -e

# Устанавливаем umask до сброса привилегий:
# 0022 → файлы 644, директории 755 — мир может читать.
# Это критично: telegram-bot-api контейнер (другой UID) должен
# иметь возможность stat() файлов в /downloads/fileserver/
umask 0022

# ── Права на смонтированных томах (нужны root-права, только здесь) ────────────
chown -R botuser:botuser /downloads /data 2>/dev/null || true

# ── Quick Tunnel: подставляем URL если PUBLIC_BASE_URL не задан вручную ────────
# Схема: cf-entrypoint.sh пишет URL в /cf-url/public_url после старта тоннеля.
# Бот ждёт до 90 сек (cloudflared получает URL за ~10-15 сек).
# Если CLOUDFLARE_TUNNEL_TOKEN задан (named tunnel) — PUBLIC_BASE_URL берётся из .env,
# ждать не нужно.
CF_URL_FILE="/cf-url/public_url"

if [ -z "$PUBLIC_BASE_URL" ]; then
    echo "[entrypoint] PUBLIC_BASE_URL не задан — проверяю Quick Tunnel..."
    # Запоминаем stale URL (если есть), чтобы не принять его за новый
    STALE_URL=""
    if [ -f "$CF_URL_FILE" ] && [ -s "$CF_URL_FILE" ]; then
        STALE_URL="$(cat "$CF_URL_FILE" | tr -d '[:space:]')"
        # Если файл содержит URL (не STARTING) — это stale данные от прошлого запуска
        case "$STALE_URL" in
            https://*trycloudflare.com)
                echo "[entrypoint] Обнаружен stale URL от прошлого запуска: $STALE_URL — ждём новый"
                ;;
            *)
                STALE_URL=""  # STARTING или мусор — не считаем stale
                ;;
        esac
    fi
    # Ждём до 3 минут (90 итераций × 2с) — cloudflared иногда запускается медленно
    i=0
    while [ $i -lt 90 ]; do
        if [ -f "$CF_URL_FILE" ] && [ -s "$CF_URL_FILE" ]; then
            CF_URL="$(cat "$CF_URL_FILE" | tr -d '[:space:]')"
            # Валидируем формат URL
            if echo "$CF_URL" | grep -qE '^https://[a-zA-Z0-9-]+\.trycloudflare\.com$'; then
                # Пропускаем stale URL от прошлого запуска (ждём STARTING → новый URL)
                if [ -n "$STALE_URL" ] && [ "$CF_URL" = "$STALE_URL" ]; then
                    [ $((i % 10)) -eq 0 ] && echo "[entrypoint] Всё ещё stale URL, ждём обновление... ($i/90)"
                else
                    export PUBLIC_BASE_URL="$CF_URL"
                    echo "[entrypoint] PUBLIC_BASE_URL из Quick Tunnel: $PUBLIC_BASE_URL"
                    break
                fi
            elif [ "$CF_URL" = "STARTING" ]; then
                # cloudflared ещё запускается — стираем stale URL (значит cf-entrypoint обновил файл)
                STALE_URL=""
                [ $((i % 5)) -eq 0 ] && echo "[entrypoint] cloudflared запускается... ($i/90)"
            elif [ -n "$CF_URL" ]; then
                echo "[entrypoint] WARN: отклонён подозрительный CF URL: $CF_URL"
            fi
        fi
        sleep 2
        i=$((i + 1))
    done
    if [ -z "$PUBLIC_BASE_URL" ]; then
        # Последний шанс: если stale URL — лучше использовать его, чем ничего
        if [ -n "$STALE_URL" ]; then
            export PUBLIC_BASE_URL="$STALE_URL"
            echo "[entrypoint] WARN: используем предыдущий URL туннеля (может не работать): $PUBLIC_BASE_URL"
        elif [ -n "$DIRECT_BASE_URL" ]; then
            echo "[entrypoint] Quick Tunnel не найден, но DIRECT_BASE_URL задан: $DIRECT_BASE_URL — файловый сервер будет доступен по IP"
        else
            echo "[entrypoint] Quick Tunnel URL не найден за 3 мин — файловый сервер отключён (режим Telegram API)"
        fi
    fi
else
    echo "[entrypoint] PUBLIC_BASE_URL задан вручную: $PUBLIC_BASE_URL"
fi

if [ -n "$DIRECT_BASE_URL" ]; then
    echo "[entrypoint] DIRECT_BASE_URL задан: $DIRECT_BASE_URL (прямой доступ по IP)"
fi

# ── Снижаем привилегии и запускаем бота ───────────────────────────────────────
# gosu: exec заменяет shell → PID 1 = python → SIGTERM доходит до бота корректно.
# "$@" пробрасывает CMD из Dockerfile ("python" "bot.py").
exec gosu botuser "$@"
