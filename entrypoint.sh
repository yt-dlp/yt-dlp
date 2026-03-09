#!/bin/sh
# Точка входа бота (для запуска без Docker).
# В Docker используется telegram_bot/entrypoint.sh (с gosu).
#
# Quick tunnel: если PUBLIC_BASE_URL не задан — ждёт URL от cloudflared
#               (записывается в /cf-url/public_url).
# Named tunnel / прямой IP: PUBLIC_BASE_URL уже в .env — запускает сразу.

CF_URL_FILE="/cf-url/public_url"

# Автозаполнение PUBLIC_BASE_URL только в quick tunnel режиме:
# - PUBLIC_BASE_URL пустой (не задан в .env)
# - CLOUDFLARE_TUNNEL_TOKEN тоже пустой (иначе это named tunnel — URL задаётся вручную)
# - том /cf-url примонтирован (значит cloudflared используется)
if [ -z "$PUBLIC_BASE_URL" ] && [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ] && [ -d "/cf-url" ]; then
    echo "[bot] Quick tunnel mode: ждём URL от cloudflared (max 3 мин)..."
    # Запоминаем stale URL от предыдущего запуска
    STALE_URL=""
    if [ -f "$CF_URL_FILE" ] && [ -s "$CF_URL_FILE" ]; then
        _CONTENT="$(cat "$CF_URL_FILE" | tr -d '[:space:]')"
        case "$_CONTENT" in
            https://*trycloudflare.com) STALE_URL="$_CONTENT" ;;
        esac
    fi
    for i in $(seq 1 90); do
        if [ -f "$CF_URL_FILE" ]; then
            CF_CONTENT="$(cat "$CF_URL_FILE" | tr -d '[:space:]')"
            case "$CF_CONTENT" in
                https://*trycloudflare.com)
                    if [ -n "$STALE_URL" ] && [ "$CF_CONTENT" = "$STALE_URL" ]; then
                        [ $((i % 10)) -eq 0 ] && echo "[bot] Stale URL, ждём обновление... ($i/90)"
                    else
                        PUBLIC_BASE_URL="$CF_CONTENT"
                        export PUBLIC_BASE_URL
                        echo "[bot] PUBLIC_BASE_URL=$PUBLIC_BASE_URL"
                        break
                    fi
                    ;;
                STARTING)
                    STALE_URL=""
                    [ $((i % 5)) -eq 0 ] && echo "[bot] cloudflared запускается... ($i/90)"
                    ;;
                *)
                    echo "[bot] Неизвестное содержимое $CF_URL_FILE: '$CF_CONTENT', ждём..."
                    ;;
            esac
        fi
        sleep 2
    done
    if [ -z "$PUBLIC_BASE_URL" ]; then
        if [ -n "$STALE_URL" ]; then
            PUBLIC_BASE_URL="$STALE_URL"
            export PUBLIC_BASE_URL
            echo "[bot] WARN: используем предыдущий URL туннеля: $PUBLIC_BASE_URL"
        else
            echo "[bot] Предупреждение: URL тоннеля не получен, бот запустится без раздачи ссылок"
        fi
    fi
fi

exec "$@"
