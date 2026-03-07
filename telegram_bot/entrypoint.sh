#!/bin/sh
set -e

# Исправляем права на примонтированных томах.
# Запускается от root — это единственный момент когда нужны root-права.
# 2>/dev/null: игнорируем ошибки если том read-only (telegram-bot-api volume).
chown -R botuser:botuser /downloads /data 2>/dev/null || true

# Передаём управление боту от имени botuser (снижаем привилегии).
# gosu идентичен su-exec: exec заменяет shell → PID 1 = python, SIGTERM доходит до бота.
exec gosu botuser "$@"
