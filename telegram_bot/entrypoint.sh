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
    i=0
    while [ $i -lt 45 ]; do
        if [ -f "$CF_URL_FILE" ] && [ -s "$CF_URL_FILE" ]; then
            CF_URL="$(cat "$CF_URL_FILE" | tr -d '[:space:]')"
            # HIGH-6: validate CF_URL matches expected Cloudflare tunnel pattern
            if echo "$CF_URL" | grep -qE '^https://[a-zA-Z0-9-]+\.trycloudflare\.com$'; then
                export PUBLIC_BASE_URL="$CF_URL"
                echo "[entrypoint] PUBLIC_BASE_URL из Quick Tunnel: $PUBLIC_BASE_URL"
                break
            elif [ -n "$CF_URL" ]; then
                echo "[entrypoint] WARN: отклонён подозрительный CF URL: $CF_URL"
            fi
        fi
        sleep 2
        i=$((i + 1))
    done
    if [ -z "$PUBLIC_BASE_URL" ]; then
        echo "[entrypoint] Quick Tunnel URL не найден за 90 сек — файловый сервер отключён (режим Telegram API)"
    fi
else
    echo "[entrypoint] PUBLIC_BASE_URL задан вручную: $PUBLIC_BASE_URL"
fi

# ── Снижаем привилегии и запускаем бота ───────────────────────────────────────
# gosu: exec заменяет shell → PID 1 = python → SIGTERM доходит до бота корректно.
# "$@" пробрасывает CMD из Dockerfile ("python" "bot.py").
exec gosu botuser "$@"
