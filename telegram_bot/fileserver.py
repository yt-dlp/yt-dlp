"""
Встроенный HTTP-сервер для раздачи скачанных файлов по ссылке.

Логика:
  - Каждый файл регистрируется под уникальным UUID-токеном.
  - Ссылка вида:  http(s)://<PUBLIC_BASE_URL>/dl/<token>
  - Файл удаляется СРАЗУ после первого успешного скачивания
    по ссылке (или по истечению TTL, если ссылку так и не открыли).
  - Каждый час запускается фоновая очистка просроченных файлов.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from aiohttp import web

logger = logging.getLogger(__name__)


# ── Реестр файлов ────────────────────────────────────────────────────────────────

@dataclass
class _FileEntry:
    path: Path
    filename: str          # оригинальное имя для Content-Disposition
    expires_at: float      # unix timestamp


_registry: dict[str, _FileEntry] = {}


def register_file(path: Path, ttl_seconds: int = 86400) -> str:
    """
    Зарегистрировать файл для раздачи.
    Возвращает token (часть URL).
    """
    token = uuid.uuid4().hex
    _registry[token] = _FileEntry(
        path=path,
        filename=path.name,
        expires_at=time.time() + ttl_seconds,
    )
    logger.debug("Зарегистрирован файл %s → token=%s (TTL=%ds)", path.name, token, ttl_seconds)
    return token


def _remove(token: str, reason: str = ""):
    entry = _registry.pop(token, None)
    if entry:
        entry.path.unlink(missing_ok=True)
        logger.info("Удалён файл %s (%s)", entry.filename, reason)


# ── HTTP-обработчики ──────────────────────────────────────────────────────────────

async def _handle_download(request: web.Request) -> web.StreamResponse:
    token = request.match_info["token"]

    entry = _registry.get(token)
    if entry is None:
        raise web.HTTPNotFound(reason="Файл не найден или уже удалён")

    if time.time() > entry.expires_at:
        _remove(token, reason="TTL истёк")
        raise web.HTTPGone(reason="Срок действия ссылки истёк")

    if not entry.path.exists():
        _registry.pop(token, None)
        raise web.HTTPNotFound(reason="Файл не найден на диске")

    file_size = entry.path.stat().st_size

    # Безопасное имя для заголовка (убираем кавычки)
    safe_name = entry.filename.replace('"', "_")

    response = web.StreamResponse(
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_size),
        }
    )
    await response.prepare(request)

    # Стриминг файла чанками по 256 КБ
    try:
        with entry.path.open("rb") as fh:
            while True:
                chunk = fh.read(262144)
                if not chunk:
                    break
                await response.write(chunk)
        await response.write_eof()
    except (ConnectionResetError, asyncio.CancelledError):
        logger.warning("Соединение прервано при отдаче %s", entry.filename)
        return response

    # Удаляем файл после успешной отдачи
    _remove(token, reason="успешно скачан")
    return response


async def _handle_health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


# ── Фоновая очистка ──────────────────────────────────────────────────────────────

async def _cleanup_loop():
    while True:
        await asyncio.sleep(3600)  # каждый час
        now = time.time()
        expired = [t for t, e in list(_registry.items()) if now > e.expires_at]
        for token in expired:
            _remove(token, reason="TTL истёк (cleanup)")
        if expired:
            logger.info("Очистка: удалено %d просроченных файлов", len(expired))


# ── Запуск сервера ───────────────────────────────────────────────────────────────

async def start(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    """
    Запустить HTTP-сервер раздачи файлов.
    Возвращает runner (для graceful shutdown).
    """
    app = web.Application()
    app.router.add_get("/dl/{token}", _handle_download)
    app.router.add_get("/health", _handle_health)

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    asyncio.create_task(_cleanup_loop())
    logger.info("Файловый сервер запущен на %s:%d", host, port)
    return runner
