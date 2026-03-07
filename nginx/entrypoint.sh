#!/bin/sh
# ══════════════════════════════════════════════════════════════════════════════
# nginx-ssl entrypoint: TLS-терминация для файлового сервера yt-dlp бота.
#
# Логика:
#   1. Генерирует self-signed сертификат (если нет LE cert в volume)
#   2. Применяет nginx.conf из шаблона (envsubst)
#   3. Пытается получить Let's Encrypt сертификат через HTTP-01 challenge
#      (нужен порт 80, маршрутизированный через nftables DNAT)
#   4. Запускает nginx как PID 1 + фоновый renewal loop
#
# Переменные окружения:
#   SSLIP_DOMAIN   — обязательно (например: 150-241-90-145.sslip.io)
#   HTTPS_PORT     — порт HTTPS (по умолчанию 7443)
#   CERTBOT_EMAIL  — email для Let's Encrypt (пусто → без email, --register-unsafely-without-email)
#   ENABLE_CERTBOT — "true" для включения certbot (по умолчанию true)
# ══════════════════════════════════════════════════════════════════════════════
set -e

DOMAIN="${SSLIP_DOMAIN}"
HTTPS_PORT="${HTTPS_PORT:-7443}"
CERT_DIR="/etc/nginx/ssl"
LE_DIR="/etc/letsencrypt/live/${DOMAIN}"
WEBROOT="/var/www/certbot"
ENABLE_CERTBOT="${ENABLE_CERTBOT:-true}"

mkdir -p "$CERT_DIR" "$WEBROOT"

# ── Проверка обязательных переменных ──────────────────────────────────────────
if [ -z "$DOMAIN" ]; then
    echo "[nginx-ssl] FATAL: SSLIP_DOMAIN не задан"
    echo "[nginx-ssl] Пример: SSLIP_DOMAIN=150-241-90-145.sslip.io"
    exit 1
fi

# ── Генерация nginx.conf из шаблона ──────────────────────────────────────────
envsubst '${SSLIP_DOMAIN} ${HTTPS_PORT}' \
    < /etc/nginx/templates/nginx.conf.template \
    > /etc/nginx/nginx.conf

echo "[nginx-ssl] Конфигурация: https://${DOMAIN}:${HTTPS_PORT} → ytdlp-bot:8080"

# ── Сертификат: проверяем наличие LE cert в volume ────────────────────────────
# Если LE cert уже получен ранее (persisted в volume) — копируем его.
# Если нет — генерируем self-signed (будет заменён при успешном certbot).
if [ -f "$LE_DIR/fullchain.pem" ] && [ -f "$LE_DIR/privkey.pem" ]; then
    cp -f "$LE_DIR/fullchain.pem" "$CERT_DIR/fullchain.pem"
    cp -f "$LE_DIR/privkey.pem"   "$CERT_DIR/privkey.pem"
    echo "[nginx-ssl] Let's Encrypt сертификат загружен из volume"
    HAVE_LE=1
elif [ ! -f "$CERT_DIR/fullchain.pem" ]; then
    echo "[nginx-ssl] Генерирую временный self-signed сертификат..."
    openssl req -x509 -nodes -days 3650 \
        -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out    "$CERT_DIR/fullchain.pem" \
        -subj   "/CN=${DOMAIN}" 2>/dev/null
    HAVE_LE=0
    echo "[nginx-ssl] Self-signed cert готов (EC P-256)"
else
    HAVE_LE=0
    echo "[nginx-ssl] Используется существующий сертификат"
fi

# ── Certbot: получение Let's Encrypt сертификата (фоновый процесс) ────────────
# Запускается ПОСЛЕ nginx (нужен webroot на порту 80 для ACME challenge).
# Требования:
#   - ENABLE_CERTBOT=true (по умолчанию)
#   - Порт 80 маршрутизирован через nftables DNAT на этот контейнер (10.10.2.5:80)
#
# Email необязателен: если CERTBOT_EMAIL пуст — используется --register-unsafely-without-email.
# Если порт 80 НЕ маршрутизирован — certbot gracefully fail, бот работает
# с self-signed сертификатом (шифрование есть, верификация — нет).
if [ "$ENABLE_CERTBOT" = "true" ]; then
    # Формируем аргументы certbot
    if [ -n "$CERTBOT_EMAIL" ]; then
        CERTBOT_AUTH="--email $CERTBOT_EMAIL --agree-tos --non-interactive"
    else
        CERTBOT_AUTH="--agree-tos --register-unsafely-without-email --non-interactive"
    fi

    (
        # Ждём пока nginx стартует
        sleep 5

        if [ "$HAVE_LE" = "0" ]; then
            echo "[nginx-ssl] Запрашиваю Let's Encrypt сертификат для ${DOMAIN}..."
            echo "[nginx-ssl] (нужен nftables DNAT: порт 80 → 10.10.2.5:80)"
            if [ -n "$CERTBOT_EMAIL" ]; then
                echo "[nginx-ssl] Email: ${CERTBOT_EMAIL}"
            else
                echo "[nginx-ssl] Email: не задан (--register-unsafely-without-email)"
            fi
            if certbot certonly --webroot -w "$WEBROOT" \
                -d "$DOMAIN" \
                $CERTBOT_AUTH \
                --preferred-challenges http 2>&1; then

                if [ -f "$LE_DIR/fullchain.pem" ]; then
                    cp -f "$LE_DIR/fullchain.pem" "$CERT_DIR/fullchain.pem"
                    cp -f "$LE_DIR/privkey.pem"   "$CERT_DIR/privkey.pem"
                    nginx -s reload
                    echo "[nginx-ssl] ✓ Let's Encrypt сертификат установлен!"
                fi
            else
                echo ""
                echo "[nginx-ssl] ⚠ certbot не смог получить сертификат"
                echo "[nginx-ssl]   HTTPS работает с self-signed cert (шифрование есть)"
                echo "[nginx-ssl]   Для LE cert добавьте в nftables:"
                echo "[nginx-ssl]     fib daddr type local tcp dport 80 dnat to 10.10.2.5:80"
                echo "[nginx-ssl]   и перезапустите: docker restart nginx-ssl"
                echo ""
            fi
        fi

        # Renewal loop: каждые 12 часов проверяем необходимость обновления.
        # certbot renew обновляет cert только если осталось < 30 дней.
        # deploy-hook вызывается ТОЛЬКО при фактическом обновлении.
        while true; do
            sleep 43200
            certbot renew --quiet \
                --deploy-hook "cp -f ${LE_DIR}/fullchain.pem ${CERT_DIR}/fullchain.pem && \
                               cp -f ${LE_DIR}/privkey.pem   ${CERT_DIR}/privkey.pem && \
                               nginx -s reload && \
                               echo '[nginx-ssl] Сертификат обновлён'" \
                2>/dev/null || true
        done
    ) &
    echo "[nginx-ssl] Certbot запущен в фоне (renewal каждые 12ч)"
else
    echo "[nginx-ssl] ENABLE_CERTBOT=false — Let's Encrypt отключён"
    echo "[nginx-ssl] HTTPS работает с self-signed сертификатом"
fi

# ── Запуск nginx как PID 1 (получает SIGTERM при остановке контейнера) ─────────
echo "[nginx-ssl] nginx запущен: https://${DOMAIN}:${HTTPS_PORT}"
exec nginx -g "daemon off;"
