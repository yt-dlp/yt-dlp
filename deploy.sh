#!/usr/bin/env bash
# Сборка и запуск Docker-контейнеров yt-dlp бота.
#
# Использование:
#   ./deploy.sh                — полная пересборка + запуск (все контейнеры + nginx-ssl)
#   ./deploy.sh build          — только сборка всех контейнеров
#   ./deploy.sh build nginx-ssl— пересборка только nginx-ssl
#   ./deploy.sh up             — запуск без пересборки
#   ./deploy.sh restart        — перезапуск всех контейнеров
#   ./deploy.sh restart nginx-ssl — перезапуск только nginx-ssl
#   ./deploy.sh down           — остановка всех контейнеров
#   ./deploy.sh logs           — логи всех контейнеров (follow)
#   ./deploy.sh logs bot       — логи бота (follow)
#   ./deploy.sh logs nginx     — логи nginx-ssl (follow)
#   ./deploy.sh logs nginx 50  — последние 50 строк nginx-ssl
set -euo pipefail
cd "$(dirname "$0")"

export GIT_COMMIT
GIT_COMMIT=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "dev")

COMPOSE="docker compose --profile ssl"

case "${1:-all}" in
    build)
        echo "Building with GIT_COMMIT=$GIT_COMMIT ..."
        if [ -n "${2:-}" ]; then
            $COMPOSE build "$2"
        else
            $COMPOSE build
        fi
        ;;
    up)
        $COMPOSE up -d
        ;;
    restart)
        if [ -n "${2:-}" ]; then
            docker restart "$2"
        else
            $COMPOSE restart
        fi
        ;;
    down)
        $COMPOSE down
        ;;
    logs)
        case "${2:-all}" in
            bot)
                docker logs -f ${3:+--tail "$3"} ytdlp-bot
                ;;
            nginx|nginx-ssl)
                docker logs -f ${3:+--tail "$3"} nginx-ssl
                ;;
            tunnel|cloudflared)
                docker logs -f ${3:+--tail "$3"} cloudflared
                ;;
            api|telegram-bot-api)
                docker logs -f ${3:+--tail "$3"} telegram-bot-api
                ;;
            all|"")
                $COMPOSE logs -f
                ;;
            *)
                docker logs -f ${3:+--tail "$3"} "$2"
                ;;
        esac
        ;;
    all|"")
        echo "Building with GIT_COMMIT=$GIT_COMMIT ..."
        $COMPOSE up -d --build
        echo "Done. Version commit: $GIT_COMMIT"
        ;;
    *)
        echo "Usage: $0 {build|up|restart|down|logs} [service] [tail-lines]" >&2
        exit 1
        ;;
esac
