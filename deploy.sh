#!/usr/bin/env bash
# Сборка и запуск Docker-контейнеров yt-dlp бота.
# Использование:
#   ./deploy.sh              — сборка + запуск
#   ./deploy.sh build        — только сборка
#   ./deploy.sh up           — только запуск
#   ./deploy.sh down         — остановка
#   ./deploy.sh logs         — логи бота
set -euo pipefail
cd "$(dirname "$0")"

export GIT_COMMIT
GIT_COMMIT=$(git rev-parse --short=7 HEAD 2>/dev/null || echo "dev")

case "${1:-all}" in
    build)
        echo "Building with GIT_COMMIT=$GIT_COMMIT ..."
        docker compose build
        ;;
    up)
        docker compose up -d
        ;;
    down)
        docker compose down
        ;;
    logs)
        docker compose logs -f ytdlp-bot
        ;;
    all|"")
        echo "Building with GIT_COMMIT=$GIT_COMMIT ..."
        docker compose build
        docker compose up -d
        echo "Done. Version commit: $GIT_COMMIT"
        ;;
    *)
        echo "Usage: $0 {build|up|down|logs}" >&2
        exit 1
        ;;
esac
