#!/bin/sh
# Точка входа контейнера cloudflared.
# Named tunnel: просто запускает cloudflared с токеном.
# Quick tunnel: запускает cloudflared, извлекает URL из логов
#               и сохраняет в /cf-url/public_url для бота.

set -e

CF_URL_FILE="/cf-url/public_url"
CF_LOG="/cf-url/cf.log"

# ── Named Tunnel (CLOUDFLARE_TUNNEL_TOKEN задан) ──────────────────────────────
if [ -n "$TUNNEL_TOKEN" ]; then
    echo "[cloudflared] Named tunnel mode"
    exec cloudflared tunnel --no-autoupdate --metrics 0.0.0.0:2000 --edge-ip-version 4 run --token "$TUNNEL_TOKEN"
fi

# ── Quick Tunnel (без токена, URL меняется при перезапуске) ───────────────────
echo "[cloudflared] Quick tunnel mode — URL появится ниже (занимает ~10 сек)"

mkdir -p /cf-url
rm -f "$CF_LOG"
# Перезаписываем старый URL до запуска cloudflared — бот увидит "STARTING"
# и не будет использовать stale URL из предыдущего сеанса.
# Используем атомарную запись: write→rename, чтобы бот не прочитал пустой файл.
echo "STARTING" > "${CF_URL_FILE}.tmp"
mv -f "${CF_URL_FILE}.tmp" "$CF_URL_FILE"
# Также убеждаемся, что файл видим по NFS/shared-volume
sync 2>/dev/null || true

# Запускаем cloudflared в фоне, логи пишем в файл
cloudflared tunnel --no-autoupdate \
    --metrics 0.0.0.0:2000 \
    --edge-ip-version 4 \
    --url "http://ytdlp-bot:${HTTP_PORT:-8080}" \
    >"$CF_LOG" 2>&1 &
CF_PID=$!

# Пробрасываем логи cloudflared в stdout сразу (видно в docker compose logs)
tail -f "$CF_LOG" &

# Ищем URL в логах (cloudflared печатает его в первые ~15 сек)
FOUND=0
for i in $(seq 1 90); do
    URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$CF_LOG" 2>/dev/null | head -1)
    if [ -n "$URL" ]; then
        # Атомарная запись: write→rename, чтобы бот не прочитал частично записанный файл
        echo "$URL" > "${CF_URL_FILE}.tmp"
        mv -f "${CF_URL_FILE}.tmp" "$CF_URL_FILE"
        sync 2>/dev/null || true
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  Cloudflare Quick Tunnel URL:                            ║"
        echo "║  $URL"
        echo "║                                                          ║"
        echo "║  Бот получит этот URL автоматически.                     ║"
        echo "║  URL изменится при следующем перезапуске cloudflared.    ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        echo ""
        FOUND=1
        break
    fi
    sleep 2
done

if [ "$FOUND" -eq 0 ]; then
    echo "[cloudflared] WARNING: URL тоннеля не найден в логах за 3 минуты"
fi

# Ждём завершения cloudflared (если упадёт — контейнер перестартует)
wait "$CF_PID"
