"""
Встроенный HTTP-сервер для раздачи скачанных файлов по токенам.

Безопасность:
  • UUID4-токен (122 бит энтропии — практически неугадываемый)
  • Необязательная HMAC-SHA256 подпись каждого токена через SERVER_SECRET (.env)
  • Rate-limiting: не более FS_RATE_LIMIT запросов с одного IP в минуту
  • Токен однократного использования — файл удаляется сразу после скачивания
  • TTL: ссылка и файл удаляются через час если никто не скачал
  • Стандартные security-заголовки (X-Content-Type-Options, X-Frame-Options, …)
  • Токен не содержит пути на диске; перебор невозможен даже без HMAC
  • HTML-страница предварительного просмотра (/info/<token>) защищает от
    случайного скачивания при предпросмотре ссылок мессенджерами

Структура URL:
  GET /info/<token>   — HTML-страница с кнопкой «Скачать»
  GET /dl/<token>     — прямое скачивание (используется кнопкой со страницы)
  GET /health         — healthcheck
"""

import asyncio
import hashlib
import hmac as _hmac_mod
import logging
import os
import shutil
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aiohttp import web

logger = logging.getLogger(__name__)

# ── Настройки безопасности ───────────────────────────────────────────────────────

# Секрет для HMAC-подписи токенов (задаётся в .env как SERVER_SECRET).
# Если не задан — токены без подписи (UUID4 = 122 бит энтропии, всё ещё безопасно).
_SERVER_SECRET: bytes = os.environ.get("SERVER_SECRET", "").encode()

# Максимум запросов с одного IP в минуту (защита от сканирования)
_RATE_LIMIT: int = int(os.environ.get("FS_RATE_LIMIT", "30"))

# ── Реестр файлов ────────────────────────────────────────────────────────────────

@dataclass
class FileEntry:
    path: Path
    filename: str
    file_size: int
    expires_at: float   # unix timestamp


# uuid_key (32 hex) → FileEntry
_registry: dict[str, FileEntry] = {}

# IP → список unix-timestamps запросов за последнюю минуту
_rate_counters: dict[str, list[float]] = defaultdict(list)


# ── Токены ───────────────────────────────────────────────────────────────────────

def _make_token() -> tuple[str, str]:
    """Создаёт токен. Возвращает (uuid_key, full_token).

    Если SERVER_SECRET задан — full_token = uuid_key + hmac16 (48 символов).
    Иначе — full_token == uuid_key (32 символа).
    """
    uuid_key = uuid.uuid4().hex  # 32 hex-символа
    if _SERVER_SECRET:
        sig = _hmac_mod.new(
            _SERVER_SECRET, uuid_key.encode(), hashlib.sha256
        ).hexdigest()[:16]
        return uuid_key, uuid_key + sig  # 48 символов
    return uuid_key, uuid_key


def _verify_token(token: str) -> Optional[str]:
    """Проверяет токен и возвращает uuid_key (32 hex) или None при ошибке."""
    token = token.strip()
    if _SERVER_SECRET:
        if len(token) != 48:
            return None
        uuid_key = token[:32]
        sig = token[32:]
        # compare_digest защищает от timing-атак
        expected = _hmac_mod.new(
            _SERVER_SECRET, uuid_key.encode(), hashlib.sha256
        ).hexdigest()[:16]
        if not _hmac_mod.compare_digest(sig, expected):
            return None
        return uuid_key
    else:
        if len(token) != 32:
            return None
        # Только hex-символы
        if not all(c in "0123456789abcdef" for c in token):
            return None
        return token


# ── Публичный API ────────────────────────────────────────────────────────────────

def register_file(path: Path, ttl_seconds: int = 3600) -> str:
    """Регистрирует уже существующий файл. Возвращает full_token."""
    uuid_key, full_token = _make_token()
    _registry[uuid_key] = FileEntry(
        path=path,
        filename=path.name,
        file_size=path.stat().st_size if path.exists() else 0,
        expires_at=time.time() + ttl_seconds,
    )
    logger.info("Зарегистрирован '%s' → %s… (TTL=%ds)", path.name, uuid_key[:8], ttl_seconds)
    return full_token


def move_and_register(src: Path, ttl_seconds: int = 3600) -> str:
    """Перемещает файл в изолированную директорию и регистрирует его.

    Возвращает full_token. Файл переносится из временной папки бота в
    /downloads/fileserver/<uuid_key>/<filename>, чтобы TTL-очистка не
    зависела от tmp_dir загрузчика.
    """
    from config import DOWNLOAD_DIR
    uuid_key, full_token = _make_token()
    serve_dir = DOWNLOAD_DIR / "fileserver" / uuid_key
    serve_dir.mkdir(parents=True, exist_ok=True)
    dest = serve_dir / src.name
    shutil.move(str(src), str(dest))
    _registry[uuid_key] = FileEntry(
        path=dest,
        filename=dest.name,
        file_size=dest.stat().st_size,
        expires_at=time.time() + ttl_seconds,
    )
    logger.info(
        "Перемещён и зарегистрирован '%s' → %s… (TTL=%ds)", src.name, uuid_key[:8], ttl_seconds
    )
    return full_token


def get_entry(full_token: str) -> Optional[FileEntry]:
    """Возвращает FileEntry по токену (без удаления) или None."""
    uuid_key = _verify_token(full_token)
    if not uuid_key:
        return None
    entry = _registry.get(uuid_key)
    if entry and time.time() > entry.expires_at:
        _remove(uuid_key, "TTL истёк (get_entry)")
        return None
    return entry


def unregister(full_token: str, *, delete_file: bool = False) -> None:
    """Убирает токен из реестра.

    delete_file=False (по умолчанию): файл остаётся на диске — использовать
    когда файл будет удалён отправителем (например, после send_document).
    delete_file=True: удаляет файл и его директорию.
    """
    uuid_key = (full_token[:32] if len(full_token) >= 32 else full_token)
    entry = _registry.pop(uuid_key, None)
    if entry is None:
        return
    if delete_file:
        entry.path.unlink(missing_ok=True)
        _rmdir_safe(entry.path.parent)
        logger.debug("Токен %s… отозван + файл удалён", uuid_key[:8])
    else:
        logger.debug("Токен %s… отозван (файл сохранён)", uuid_key[:8])


# ── Внутренние утилиты ───────────────────────────────────────────────────────────

def _remove(uuid_key: str, reason: str = "") -> None:
    entry = _registry.pop(uuid_key, None)
    if entry:
        entry.path.unlink(missing_ok=True)
        _rmdir_safe(entry.path.parent)
        logger.info("Файл '%s' удалён (%s)", entry.filename, reason)


def _rmdir_safe(d: Path) -> None:
    """Удаляет директорию если пустая."""
    try:
        d.rmdir()
    except OSError:
        pass


def _check_rate_limit(ip: str) -> bool:
    """True если IP ещё не исчерпал лимит запросов."""
    now = time.time()
    hits = _rate_counters[ip]
    _rate_counters[ip] = [h for h in hits if now - h < 60]
    if len(_rate_counters[ip]) >= _RATE_LIMIT:
        return False
    _rate_counters[ip].append(now)
    return True


def _fmt_size(n: int) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ТБ"


def _fmt_ttl(seconds: int) -> str:
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}ч {m}м" if m else f"{h}ч"
    return f"{m}м {s}с" if m else f"{s}с"


# ── Security headers (применяются ко всем ответам) ───────────────────────────────

_SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "X-Robots-Tag": "noindex, nofollow",
}

# ── HTML info page ───────────────────────────────────────────────────────────────

_INFO_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Скачать файл</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e2e8f0;
         display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px}}
    .card{{background:#1e2130;border-radius:16px;padding:36px 32px;max-width:480px;width:100%;
           box-shadow:0 8px 32px rgba(0,0,0,.4)}}
    .icon{{font-size:2.5rem;margin-bottom:16px}}
    h2{{font-size:1.1rem;font-weight:600;word-break:break-word;margin-bottom:8px;color:#f1f5f9}}
    .meta{{color:#94a3b8;font-size:.9rem;margin-bottom:28px;line-height:1.7}}
    .btn{{display:block;width:100%;padding:15px;background:#3b82f6;color:#fff;border:none;
          border-radius:10px;font-size:1rem;font-weight:700;text-align:center;
          text-decoration:none;cursor:pointer;transition:background .15s}}
    .btn:hover{{background:#2563eb}}
    .warn{{background:#1c1917;border-left:3px solid #f59e0b;border-radius:0 8px 8px 0;
           padding:12px 16px;font-size:.82rem;color:#fcd34d;margin-top:20px;line-height:1.5}}
  </style>
</head>
<body>
<div class="card">
  <div class="icon">📁</div>
  <h2>{safe_name}</h2>
  <p class="meta">
    📦 {size_str}<br>
    ⏱ Ссылка истекает через <strong>{ttl_str}</strong><br>
    🗑 Файл удаляется после скачивания
  </p>
  <a class="btn" href="/dl/{token}">⬇️ Скачать</a>
  <div class="warn">
    ⚠️ Ссылка одноразовая — после первого скачивания файл будет автоматически удалён.
    Убедитесь, что скачиваете в надёжное место.
  </div>
</div>
</body>
</html>
"""


# ── HTTP handlers ────────────────────────────────────────────────────────────────

async def _handle_info(request: web.Request) -> web.Response:
    """HTML-страница с информацией о файле и кнопкой «Скачать»."""
    token = request.match_info["token"]
    ip = request.remote or "unknown"

    if not _check_rate_limit(ip):
        raise web.HTTPTooManyRequests(
            reason="Слишком много запросов. Попробуйте через минуту.",
            headers=_SEC_HEADERS,
        )

    uuid_key = _verify_token(token)
    if uuid_key is None:
        raise web.HTTPNotFound(headers=_SEC_HEADERS)

    entry = _registry.get(uuid_key)
    if entry is None:
        raise web.HTTPGone(
            reason="Файл не найден или ссылка уже использована.",
            headers=_SEC_HEADERS,
        )

    if time.time() > entry.expires_at:
        _remove(uuid_key, "TTL истёк (info)")
        raise web.HTTPGone(reason="Срок действия ссылки истёк.", headers=_SEC_HEADERS)

    remaining = int(entry.expires_at - time.time())
    safe_name = entry.filename.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    html = _INFO_TEMPLATE.format(
        safe_name=safe_name,
        size_str=_fmt_size(entry.file_size),
        ttl_str=_fmt_ttl(remaining),
        token=token,
    )
    return web.Response(
        text=html,
        content_type="text/html",
        charset="utf-8",
        headers=_SEC_HEADERS,
    )


async def _handle_download(request: web.Request) -> web.StreamResponse:
    """Стриминг файла клиенту с последующим удалением."""
    token = request.match_info["token"]
    ip = request.remote or "unknown"

    if not _check_rate_limit(ip):
        raise web.HTTPTooManyRequests(
            reason="Слишком много запросов.",
            headers=_SEC_HEADERS,
        )

    uuid_key = _verify_token(token)
    if uuid_key is None:
        raise web.HTTPNotFound(headers=_SEC_HEADERS)

    entry = _registry.get(uuid_key)
    if entry is None:
        raise web.HTTPGone(
            reason="Файл не найден или ссылка уже использована.",
            headers=_SEC_HEADERS,
        )

    if time.time() > entry.expires_at:
        _remove(uuid_key, "TTL истёк (download)")
        raise web.HTTPGone(reason="Срок действия ссылки истёк.", headers=_SEC_HEADERS)

    if not entry.path.exists():
        _registry.pop(uuid_key, None)
        raise web.HTTPNotFound(
            reason="Файл не найден на диске.",
            headers=_SEC_HEADERS,
        )

    file_size = entry.path.stat().st_size
    safe_name = entry.filename.replace('"', "_")

    response = web.StreamResponse(
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Type": "application/octet-stream",
            "Content-Length": str(file_size),
            **_SEC_HEADERS,
        }
    )
    await response.prepare(request)

    downloaded_ok = False
    try:
        with entry.path.open("rb") as fh:
            while True:
                chunk = fh.read(524288)  # 512 KB chunks
                if not chunk:
                    break
                await response.write(chunk)
        await response.write_eof()
        downloaded_ok = True
    except (ConnectionResetError, asyncio.CancelledError):
        logger.warning("Соединение прервано при отдаче '%s' клиенту %s", entry.filename, ip)
        return response
    except Exception as e:
        logger.error("Ошибка при отдаче '%s': %s", entry.filename, e)
        return response

    if downloaded_ok:
        logger.info("Файл '%s' успешно отдан клиенту %s", safe_name, ip)
        _remove(uuid_key, "успешно скачан")

    return response


async def _handle_health(request: web.Request) -> web.Response:
    return web.Response(
        text="ok",
        headers={**_SEC_HEADERS, "Cache-Control": "no-store"},
    )


# ── Фоновая очистка ──────────────────────────────────────────────────────────────

async def _cleanup_loop() -> None:
    """Каждый час: удаляет файлы с истёкшим TTL и очищает rate-counters."""
    while True:
        await asyncio.sleep(3600)
        now = time.time()

        # Удаляем просроченные файлы
        expired = [k for k, e in list(_registry.items()) if now > e.expires_at]
        for key in expired:
            _remove(key, "TTL истёк (cleanup)")

        # Чистим rate-counters от старых записей
        cutoff = now - 60
        for ip in list(_rate_counters.keys()):
            _rate_counters[ip] = [h for h in _rate_counters[ip] if h > cutoff]
            if not _rate_counters[ip]:
                del _rate_counters[ip]

        if expired:
            logger.info("Очистка файлового сервера: удалено %d файлов", len(expired))


# ── Запуск / остановка ───────────────────────────────────────────────────────────

_runner: Optional[web.AppRunner] = None
_cleanup_task: Optional[asyncio.Task] = None


async def start(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    """Запускает HTTP-сервер и фоновую очистку."""
    global _runner, _cleanup_task

    app = web.Application()
    app.router.add_get("/info/{token}", _handle_info)
    app.router.add_get("/dl/{token}", _handle_download)
    app.router.add_get("/health", _handle_health)

    _runner = web.AppRunner(app, access_log=None)
    await _runner.setup()
    site = web.TCPSite(_runner, host, port)
    await site.start()

    _cleanup_task = asyncio.create_task(_cleanup_loop())

    hmac_status = "HMAC подпись включена ✓" if _SERVER_SECRET else "HMAC выключен (только UUID4)"
    logger.info(
        "Файловый сервер запущен: http://%s:%d  |  %s  |  rate-limit=%d req/min",
        host, port, hmac_status, _RATE_LIMIT,
    )
    return _runner


async def stop() -> None:
    """Graceful shutdown файлового сервера."""
    global _runner, _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        _cleanup_task = None
    if _runner:
        await _runner.cleanup()
        _runner = None
    logger.info("Файловый сервер остановлен")
