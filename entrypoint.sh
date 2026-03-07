#!/bin/sh
# Точка входа бота.
# Quick tunnel: если PUBLIC_BASE_URL не задан — ждёт URL от cloudflared
#               (записывается в /cf-url/public_url).
# Named tunnel / прямой IP: PUBLIC_BASE_URL уже в .env — запускает сразу.

CF_URL_FILE="/cf-url/public_url"

# Автозаполнение PUBLIC_BASE_URL только в quick tunnel режиме:
# - PUBLIC_BASE_URL пустой (не задан в .env)
# - CLOUDFLARE_TUNNEL_TOKEN тоже пустой (иначе это named tunnel — URL задаётся вручную)
# - том /cf-url примонтирован (значит cloudflared используется)
if [ -z "$PUBLIC_BASE_URL" ] && [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ] && [ -d "/cf-url" ]; then
    echo "[bot] Quick tunnel mode: ждём URL от cloudflared (max 2 мин)..."
    for i in $(seq 1 40); do
        if [ -f "$CF_URL_FILE" ]; then
            PUBLIC_BASE_URL="$(cat "$CF_URL_FILE")"
            export PUBLIC_BASE_URL
            echo "[bot] PUBLIC_BASE_URL=$PUBLIC_BASE_URL"
            break
        fi
        sleep 3
    done
    if [ -z "$PUBLIC_BASE_URL" ]; then
        echo "[bot] Предупреждение: URL тоннеля не получен, бот запустится без раздачи ссылок"
    fi
fi

exec "$@"
