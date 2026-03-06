#!/bin/sh
# Fix permissions on mounted volumes, then drop to botuser
chown -R botuser:botuser /downloads /data 2>/dev/null || true
exec su-exec botuser python bot.py
