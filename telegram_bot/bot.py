#!/usr/bin/env python3
"""
YT-DLP Telegram Bot — русскоязычный интерфейс
"""

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
import traceback
from dataclasses import asdict
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from telegram import (
    Bot,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputFile,
    InputTextMessageContent,
    Message,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

import config
import database as db
import fileserver
from downloader import (
    DownloadResult,
    FormatInfo,
    ProgressTracker,
    VideoInfo,
    download_video,
    get_audio_formats,
    get_best_video_formats,
    get_video_info,
    is_supported_url,
)

# ── Logging ──────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class _TokenMaskFilter(logging.Filter):
    """Заменяет токен бота на <TOKEN> во всех лог-сообщениях."""
    def __init__(self, token: str):
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._token:
            return True
        record.msg = str(record.msg).replace(self._token, "<TOKEN>")
        if record.args:
            args = record.args if isinstance(record.args, tuple) else (record.args,)
            record.args = tuple(
                a.replace(self._token, "<TOKEN>") if isinstance(a, str) else a
                for a in args
            )
        return True

# ── Session state keys ───────────────────────────────────────────────────────────
KEY_VIDEO_INFO  = "video_info"
KEY_DOWNLOAD_ID = "download_id"
KEY_PENDING_URL = "pending_url"
KEY_ORIG_URL    = "original_url"   # сохраняем оригинальный URL (с list=) для плейлиста
KEY_MAIN_MENU_MSG = "main_menu_msg_id"  # message_id последнего сообщения главного меню
KEY_QUALITY_MSG   = "quality_menu_msg_id"  # message_id меню выбора качества (для удаления при новой ссылке)


# ── Session serialization (persist quality-menu state across restarts) ───────────

def _serialize_video_info(info: VideoInfo) -> str:
    return json.dumps(asdict(info))


def _deserialize_video_info(data: str) -> VideoInfo:
    d = json.loads(data)
    formats = [FormatInfo(**f) for f in d.pop("formats", [])]
    return VideoInfo(formats=formats, **d)


# ── Поддерживаемые платформы (текст для /start и /help) ─────────────────────────

SUPPORTED_SITES_TEXT = (
    "📌 <b>Поддерживаемые платформы:</b>\n"
    "• <b>Видео:</b> YouTube, Vimeo, Dailymotion, Rutube, ВКонтакте, OK.ru\n"
    "• <b>Соцсети:</b> Instagram, TikTok, Twitter/X, Facebook, Pinterest\n"
    "• <b>Стриминг:</b> Twitch, Kick, YouTube Live\n"
    "• <b>Музыка:</b> SoundCloud, Bandcamp, Mixcloud, YouTube Music\n"
    "• <b>Новости/прочее:</b> Reddit, Telegram, Coub, и 1000+ других\n"
    "(<a href='https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md'>полный список</a>)"
)


# ── Декораторы ───────────────────────────────────────────────────────────────────

def require_auth(func):
    """Отклоняет неавторизованных пользователей."""
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.upsert_user(user.id, user.username, user.full_name)
        if db.is_admin(user.id):
            return await func(update, ctx)
        if not db.is_authorized(user.id):
            row = db.get_user(user.id)
            if row and not row["is_approved"] and not row["is_banned"]:
                await update.effective_message.reply_text(
                    "⏳ Ваша заявка на доступ ожидает одобрения администратора.\n"
                    "Вы получите уведомление после одобрения."
                )
            elif row and row["is_banned"]:
                await update.effective_message.reply_text("🚫 Вы заблокированы и не можете использовать этого бота.")
            else:
                await _send_access_request(update, ctx)
            return
        return await func(update, ctx)
    return wrapper


def require_admin(func):
    """Отклоняет не-администраторов."""
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not db.is_admin(user.id):
            await update.effective_message.reply_text("🚫 Требуется доступ администратора.")
            return
        return await func(update, ctx)
    return wrapper


# ── Запрос доступа ───────────────────────────────────────────────────────────────

async def _send_access_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)

    if config.REGISTRATION_MODE == "open":
        db.approve_user(user.id, 0)
        await update.effective_message.reply_text(
            "✅ Регистрация открыта! Вы получили доступ.\n"
            "Отправьте /start для начала."
        )
        return

    await update.effective_message.reply_text(
        "👋 Добро пожаловать! Это приватный бот.\n\n"
        "Ваша заявка на доступ отправлена администратору.\n"
        "Пожалуйста, ожидайте одобрения."
    )

    # Уведомляем администраторов
    uname = f"@{_esc(user.username)}" if user.username else _esc(user.full_name)
    msg = (
        f"🔔 <b>Новая заявка на доступ</b>\n\n"
        f"👤 Имя: {_esc(user.full_name)}\n"
        f"🔗 Username: {uname}\n"
        f"🆔 ID: <code>{user.id}</code>"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{user.id}"),
        InlineKeyboardButton("🚫 Отклонить", callback_data=f"deny:{user.id}"),
    ]])
    for admin_id in config.ADMIN_IDS:
        try:
            await ctx.bot.send_message(admin_id, msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except TelegramError:
            pass


# ── Версия бота ──────────────────────────────────────────────────────────────────

def _get_bot_version() -> str:
    """Возвращает версию бота: <yt-dlp version>-<git commit hash>.

    Пример: 2026.03.03-1feacfc
    """
    # yt-dlp версия (из установленного пакета)
    try:
        from yt_dlp.version import __version__ as ytdlp_ver
    except Exception:
        ytdlp_ver = "unknown"
    # Git commit hash бота (из ENV → файла .git_commit → git → "dev")
    commit = os.environ.get("GIT_COMMIT", "")
    if not commit or commit == "dev":
        try:
            commit = open(os.path.join(os.path.dirname(__file__) or ".", ".git_commit")).read().strip()
        except Exception:
            pass
    if not commit or commit == "dev":
        try:
            import subprocess
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short=7", "HEAD"],
                cwd=os.path.dirname(__file__) or ".",
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).decode().strip()
        except Exception:
            commit = "dev"
    return f"{ytdlp_ver}-{commit[:7]}"


BOT_VERSION = _get_bot_version()


# ── Основные команды ─────────────────────────────────────────────────────────────

def _build_main_menu(user_obj) -> tuple[str, InlineKeyboardMarkup]:
    """Возвращает (текст, клавиатура) главного меню для авторизованного пользователя."""
    text = (
        f"👋 Привет, <b>{_esc(user_obj.first_name)}</b>!\n\n"
        "Я помогу тебе скачать видео или аудио с популярных сайтов.\n"
        "Просто отправь мне ссылку на видео!\n\n"
        + SUPPORTED_SITES_TEXT +
        "\n\n📋 <b>Команды:</b>\n"
        "/help — справка\n"
        "/history — история загрузок\n"
        "/status — статус бота\n\n"
        f"<code>v{BOT_VERSION}</code>"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Справка", callback_data="menu:help"),
            InlineKeyboardButton("📜 История", callback_data="menu:history"),
            InlineKeyboardButton("📊 Статус", callback_data="menu:status"),
        ]
    ])
    return text, keyboard


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)

    if db.is_admin(user.id) or db.is_authorized(user.id):
        # Удаляем предыдущее сообщение главного меню, чтобы не накапливались
        prev_msg_id = ctx.user_data.get(KEY_MAIN_MENU_MSG)
        if prev_msg_id:
            try:
                await ctx.bot.delete_message(chat_id=update.effective_chat.id, message_id=prev_msg_id)
            except TelegramError:
                pass
        text, keyboard = _build_main_menu(user)
        sent = await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )
        ctx.user_data[KEY_MAIN_MENU_MSG] = sent.message_id
        # Удаляем само сообщение /start чтобы не засорять чат
        try:
            await update.message.delete()
        except TelegramError:
            pass
    else:
        await _send_access_request(update, ctx)


@require_auth
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    is_adm = db.is_admin(update.effective_user.id)
    text = (
        "📖 <b>Справка по боту</b>\n\n"
        "<b>Как использовать:</b>\n"
        "1. Отправьте ссылку на видео\n"
        "2. Выберите качество или аудио\n"
        "3. Дождитесь загрузки и отправки файла\n\n"
        + SUPPORTED_SITES_TEXT +
        "\n\n⚠️ <b>Ограничения:</b>\n"
        f"• Максимальный размер файла: {config.MAX_FILE_SIZE_MB} МБ\n"
        f"• Таймаут загрузки: {config.DOWNLOAD_TIMEOUT // 60} мин\n\n"
        "<b>Команды:</b>\n"
        "/start — главное меню\n"
        "/help — эта справка\n"
        "/history — последние 10 загрузок\n"
        "/status — статус бота и диск\n"
        "/cancel — отменить текущую операцию\n"
    )
    if is_adm:
        text += (
            "\n<b>Команды администратора:</b>\n"
            "/pending — заявки на доступ\n"
            "/users — список пользователей\n"
            "/approve &lt;id&gt; — одобрить пользователя\n"
            "/deny &lt;id&gt; — отклонить пользователя\n"
            "/ban &lt;id&gt; — заблокировать\n"
            "/unban &lt;id&gt; — разблокировать\n"
            "/addadmin &lt;id&gt; — назначить администратором\n"
            "/stats — глобальная статистика\n"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@require_auth
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = db.get_user_history(update.effective_user.id, limit=10)
    if not rows:
        await update.message.reply_text("📭 История загрузок пуста.")
        return

    lines = ["📜 <b>Последние загрузки:</b>\n"]
    for i, row in enumerate(rows, 1):
        status_icon = {"done": "✅", "error": "❌", "pending": "⏳"}.get(row["status"], "•")
        title = _esc((row["title"] or row["url"])[:50])  # MEDIUM-3: escape HTML
        lines.append(f"{i}. {status_icon} {title}")
        if row["quality"]:
            lines.append(f"   └ {row['quality']}, {_human_size(row['file_size'])}")
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑 Очистить историю", callback_data="clear_history"),
        ]]),
    )


@require_auth
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    stats = db.get_global_stats()
    user_stats = db.get_user_stats(update.effective_user.id)
    disk = shutil.disk_usage(str(config.DOWNLOAD_DIR))
    disk_pct = disk.used / disk.total * 100
    disk_warn = " ⚠️" if disk_pct >= config.DISK_ALERT_THRESHOLD else ""
    text = (
        "📊 <b>Статус бота</b>\n\n"
        f"📥 Ваших загрузок: <b>{user_stats['downloads']}</b>\n"
        f"💾 Вы скачали: <b>{_human_size(user_stats['total_bytes'])}</b>\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📦 Всего загрузок: {stats['total_downloads']}\n"
        f"⏳ Ожидают одобрения: {stats['pending_requests']}\n\n"
        f"🖥 Диск: {_human_size(disk.free)} свободно / {_human_size(disk.total)} ({disk_pct:.0f}%){disk_warn}"
    )
    # Для администраторов — показываем кто именно ожидает
    if db.is_admin(update.effective_user.id) and stats['pending_requests']:
        pending = db.get_pending_users()
        lines = ["\n⏳ <b>Ожидают одобрения:</b>"]
        for r in pending:
            uname = f"@{_esc(r['username'])}" if r['username'] else _esc(r['full_name'])
            lines.append(f"• {uname} — <code>{r['user_id']}</code>")
        text += "\n".join(lines)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@require_auth
async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cancel_flag = ctx.user_data.get("cancel_flag")
    if cancel_flag is not None:
        cancel_flag[0] = True
    ctx.user_data.clear()
    await update.message.reply_text("🛑 Отменено. Отправьте новую ссылку когда будете готовы.")


@require_auth
async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Показывает клавиатуру с командами бота."""
    is_adm = db.is_admin(update.effective_user.id)
    user_buttons = [
        [
            InlineKeyboardButton("📜 История", callback_data="menu:history"),
            InlineKeyboardButton("📊 Статус", callback_data="menu:status"),
        ],
        [
            InlineKeyboardButton("❓ Справка", callback_data="menu:help"),
        ],
    ]
    admin_buttons = [
        [
            InlineKeyboardButton("⏳ Заявки (/pending)", callback_data="menu:pending"),
            InlineKeyboardButton("👥 Пользователи (/users)", callback_data="menu:users"),
        ],
        [
            InlineKeyboardButton("📊 Статистика (/stats)", callback_data="menu:stats"),
        ],
    ]
    buttons = user_buttons + (admin_buttons if is_adm else [])
    await update.message.reply_text(
        "📋 <b>Меню команд</b>\n\nВыберите действие или отправьте ссылку на видео:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ── Обработчик URL ───────────────────────────────────────────────────────────────

def _extract_urls(text: str) -> list[str]:
    """Извлекает все http(s)-ссылки из текста."""
    return re.findall(r'https?://[^\s<>"\']+', text)


def _strip_playlist_param(url: str) -> str:
    """Убирает параметры list= и index= из YouTube URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("list", None)
    params.pop("index", None)
    params.pop("start_radio", None)
    new_query = urlencode([(k, val) for k, vals in params.items() for val in vals])
    return urlunparse(parsed._replace(query=new_query))


def _is_youtube_mixed_url(url: str) -> bool:
    """True если YouTube URL содержит и v= и list= (видео + плейлист/миксTape)."""
    parsed = urlparse(url)
    if "youtube.com" not in parsed.netloc and "youtu.be" not in parsed.netloc:
        return False
    params = parse_qs(parsed.query)
    return "v" in params and "list" in params


@require_auth
async def handle_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()

    # Ищем все URL в сообщении
    urls = _extract_urls(text)
    valid_urls = [u for u in urls if is_supported_url(u)]

    if not valid_urls:
        await update.message.reply_text(
            "❓ Ссылка не распознана как поддерживаемая.\n\n"
            "Отправьте прямую ссылку на страницу видео.\n"
            + SUPPORTED_SITES_TEXT,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Удаляем оригинальное сообщение пользователя (убирает превью ссылки).
    try:
        await update.message.delete()
    except TelegramError:
        pass

    # Удаляем предыдущее меню выбора качества (если не было нажато ни одной кнопки).
    # Это очищает чат от неактуальных меню при вставке новой ссылки.
    _prev_quality_msg = ctx.user_data.pop(KEY_QUALITY_MSG, None)
    if _prev_quality_msg:
        try:
            await ctx.bot.delete_message(update.effective_chat.id, _prev_quality_msg)
        except TelegramError:
            pass  # уже удалено или бот нажал кнопку → меню трансформировалось в прогресс

    # Одна ссылка — стандартный флоу с поддержкой смешанного YouTube URL
    if len(valid_urls) == 1:
        url = valid_urls[0]
        if _is_youtube_mixed_url(url):
            clean_url = _strip_playlist_param(url)
            ctx.user_data[KEY_PENDING_URL] = clean_url
            ctx.user_data[KEY_ORIG_URL] = url
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📹 Скачать это видео", callback_data="resolve:video")],
                [InlineKeyboardButton("📋 Скачать плейлист целиком", callback_data="resolve:playlist")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
            ])
            await update.effective_chat.send_message(
                "🔗 Ссылка содержит и видео, и плейлист.\n"
                "Что вы хотите скачать?",
                reply_markup=keyboard,
            )
            return
        msg = await update.effective_chat.send_message("🔍 Получаю информацию о видео…")
        await _fetch_and_show_menu(url, msg, ctx)
        return

    # Несколько ссылок — отправляем все статусы сразу, затем получаем инфо параллельно.
    # Сессии сохраняются в БД по (chat_id, message_id), поэтому параллельное обновление
    # ctx.user_data не мешает: при нажатии кнопки бот восстанавливает данные из БД.
    batch = valid_urls[:5]
    msgs = []
    for i, url in enumerate(batch, 1):
        msg = await update.effective_chat.send_message(
            f"🔍 [{i}/{len(batch)}] Получаю информацию о видео…"
        )
        msgs.append(msg)
    await asyncio.gather(*(
        _fetch_and_show_menu(url, msg, ctx)
        for url, msg in zip(batch, msgs)
    ))


async def handle_inline_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline-режим: @botname <url> в любом чате → кнопка «Скачать».

    Результат вставляет URL как текст в текущий чат. Если это личный чат с ботом,
    handle_url обработает его автоматически.
    """
    query = update.inline_query
    user = update.effective_user

    # Проверяем авторизацию (inline не проходит через require_auth)
    if not (db.is_admin(user.id) or db.is_authorized(user.id)):
        await query.answer(
            results=[],
            switch_pm_text="🔐 Требуется доступ — нажмите для регистрации",
            switch_pm_parameter="start",
            cache_time=5,
        )
        return

    raw = (query.query or "").strip()
    if not raw:
        await query.answer(
            results=[],
            switch_pm_text="📥 Введите ссылку на видео после @botname",
            switch_pm_parameter="start",
            cache_time=5,
        )
        return

    urls = _extract_urls(raw)
    valid = [u for u in urls if is_supported_url(u)]
    if not valid:
        await query.answer(
            results=[],
            switch_pm_text="❓ Ссылка не поддерживается",
            switch_pm_parameter="start",
            cache_time=5,
        )
        return

    results = [
        InlineQueryResultArticle(
            id=f"dl_{i}",
            title=f"📥 Скачать {'видео/аудио' if i == 0 else f'ссылку {i+1}'}",
            description=u[:120],
            input_message_content=InputTextMessageContent(u),
        )
        for i, u in enumerate(valid[:5])
    ]
    await query.answer(results, cache_time=10)


async def _fetch_and_show_menu(url: str, msg: Message, ctx: ContextTypes.DEFAULT_TYPE):
    """Получает информацию о видео и показывает меню выбора качества."""
    try:
        info: VideoInfo = await get_video_info(url)
    except Exception as e:
        logger.error("get_video_info error: %s", e)
        err_str = str(e)
        friendly = _login_required_text(err_str)
        if friendly:
            await msg.edit_text(friendly, parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text(
                f"❌ Не удалось получить информацию о видео:\n<code>{_esc(err_str[:300])}</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    ctx.user_data[KEY_VIDEO_INFO] = info
    ctx.user_data[KEY_PENDING_URL] = url

    if info.is_playlist:
        await _show_playlist_menu(msg, info, ctx)
    else:
        sent = await _show_video_menu(msg, info, ctx)
        if sent:
            # Запоминаем message_id меню выбора качества — удалим при следующей ссылке.
            ctx.user_data[KEY_QUALITY_MSG] = sent.message_id
            try:
                db.save_session(sent.chat_id, sent.message_id, url, _serialize_video_info(info))
            except Exception as e:
                logger.warning("save_session failed: %s", e)


# ── Меню видео ───────────────────────────────────────────────────────────────────

def _build_quality_menu(info: VideoInfo) -> tuple[str, InlineKeyboardMarkup]:
    """Строит текст и клавиатуру меню выбора качества. Используется при показе и возврате."""
    video_fmts = get_best_video_formats(info.formats)
    likes_str = f"  👍 {_fmt_num(info.like_count)}" if info.like_count else ""
    has_oversized = any(
        (_estimate_download_size(f, info.duration or 0, audio_only=False) or 0) > config.MAX_FILE_SIZE_BYTES
        for f in video_fmts
    )
    size_note = (
        f"\n\n⚠️ — файл превышает лимит <b>{config.MAX_FILE_SIZE_MB} МБ</b>, скачивание будет отклонено"
        if has_oversized else ""
    )
    caption = (
        f"🎬 <b>{_esc(info.title)}</b>\n"
        f"👤 {_esc(info.uploader or '—')}\n"
        f"⏱ {info.duration_str}  👁 {info.views_str}{likes_str}\n"
        f"🌐 {_esc(info.extractor or '—')}\n\n"
        f"Выберите качество для загрузки:{size_note}"
    )
    buttons = []
    for f in video_fmts:
        est = _estimate_download_size(f, info.duration or 0, audio_only=False)
        too_large = est is not None and est > config.MAX_FILE_SIZE_BYTES
        size_hint = f" [{f.size_str}]" if f.filesize or f.tbr else ""
        fps_hint = f" {f.fps}fps" if f.fps and f.fps > 30 else ""
        warn = " ⚠️" if too_large else ""
        label = f"🎥 {f.resolution}{fps_hint} MP4{size_hint}{warn}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dl:v:{f.format_id}")])
    buttons.append([InlineKeyboardButton("⚡ Лучшее качество (авто)", callback_data="dl:v:best")])
    if config.ALLOW_AUDIO:
        buttons.append([InlineKeyboardButton("🎵 Аудио MP3 (192 kbps)", callback_data="dl:a:best")])
        # Альтернативные аудио-форматы объединяем в одну строку
        _alt_audio: list[InlineKeyboardButton] = []
        if config.ALLOW_OPUS:
            _alt_audio.append(InlineKeyboardButton("⚡ OPUS (быстро)", callback_data="dl:ao:best"))
        if config.ALLOW_WAV:
            _alt_audio.append(InlineKeyboardButton("🎵 WAV (PCM)", callback_data="dl:aw:best"))
        if _alt_audio:
            buttons.append(_alt_audio)
    if config.ALLOW_SUBTITLES:
        buttons.append([
            InlineKeyboardButton("📄 + Субтитры RU", callback_data="dl:s:ru"),
            InlineKeyboardButton("📄 + Субтитры EN", callback_data="dl:s:en"),
        ])
    buttons.append([
        InlineKeyboardButton("ℹ️ Подробнее", callback_data="info"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
    ])
    return caption, InlineKeyboardMarkup(buttons)


async def _show_video_menu(msg: Message, info: VideoInfo, ctx: ContextTypes.DEFAULT_TYPE):
    caption, keyboard = _build_quality_menu(info)
    if info.thumbnail:
        try:
            await msg.delete()
            return await ctx.bot.send_photo(
                msg.chat_id,
                photo=info.thumbnail,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        except TelegramError:
            # Миниатюра недоступна или сообщение уже удалено —
            # отправляем новое текстовое сообщение вместо редактирования удалённого.
            try:
                return await ctx.bot.send_message(
                    msg.chat_id,
                    text=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            except TelegramError:
                pass
    return await msg.edit_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


# ── Меню плейлиста ───────────────────────────────────────────────────────────────

async def _show_playlist_menu(msg: Message, info: VideoInfo, ctx: ContextTypes.DEFAULT_TYPE):
    if not config.ALLOW_PLAYLISTS:
        await msg.edit_text("⚠️ Загрузка плейлистов отключена администратором.")
        return

    count_str = f"{info.playlist_count} видео" if info.playlist_count else "несколько видео"
    caption = (
        f"📋 <b>Плейлист: {_esc(info.title)}</b>\n"
        f"🎬 Количество: {count_str}\n\n"
        "⚠️ Плейлисты могут быть очень большими.\n"
        "Выберите действие:"
    )
    _pl_max = config.MAX_PLAYLIST_ITEMS
    _pl_half = max(1, _pl_max // 2)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📥 Первые {_pl_half} видео (лучшее качество)", callback_data=f"pl:{_pl_half}:best")],
        [InlineKeyboardButton(f"📥 Первые {_pl_max} видео (лучшее качество)", callback_data=f"pl:{_pl_max}:best")],
        [InlineKeyboardButton(f"🎵 Только аудио — первые {_pl_half}", callback_data=f"pl:{_pl_half}:audio")],
        [InlineKeyboardButton(f"🎵 Только аудио — первые {_pl_max}", callback_data=f"pl:{_pl_max}:audio")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ])
    await msg.edit_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


# ── Callback-обработчик ──────────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    # Отвечаем на callback сразу — убирает «часики» на кнопке у пользователя.
    # Игнорируем ошибку если запрос уже протух (повторное нажатие, рестарт бота).
    try:
        await query.answer()
    except TelegramError:
        pass

    data = query.data

    # Кнопки одобрения/отклонения — обрабатываются отдельно (до auth-проверки),
    # т.к. приходят от администраторов (их авторизацию проверяет сам handler)
    if data.startswith("approve:") or data.startswith("deny:"):
        await _handle_admin_approval(query, ctx, data)
        return

    # ── Авторизация: все остальные callback требуют одобренного аккаунта ─────────
    user_is_auth = db.is_authorized(user.id) or db.is_admin(user.id)
    if not user_is_auth:
        await query.answer(
            "🚫 Доступ запрещён. Отправьте /start чтобы запросить доступ.",
            show_alert=True,
        )
        return

    # Кнопки меню /start (без скачивания)
    if data.startswith("menu:"):
        await _handle_menu_callback(query, ctx, data)
        return

    if data == "cancel":
        cancel_flag = ctx.user_data.get("cancel_flag")
        if cancel_flag is not None:
            # Загрузка активна: сигнализируем через cancel_flag.
            # _cancel_hook в progress_hook yt-dlp поднимает _DownloadCancelled
            # (BaseException) → поток корректно завершается → download_video()
            # возвращает result.error="CANCELLED" → меню качества показывается снова.
            #
            # НЕ вызываем task.cancel(): он прерывает asyncio-сторону, но поток
            # в executor продолжает работать и скачивать файл — это и есть
            # причина «кнопка Стоп не работает».
            cancel_flag[0] = True
            # Визуальный фидбек: меняем кнопку на «Останавливаем…»
            try:
                await query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⏳ Останавливаем…", callback_data="noop"),
                    ]])
                )
            except TelegramError:
                pass
            await query.answer("Останавливаем загрузку…", show_alert=False)
            return
        # Пользователь явно закрывает меню — удаляем сессию из БД
        try:
            db.delete_session(query.message.chat_id, query.message.message_id)
        except Exception:
            pass
        ctx.user_data.clear()
        # Возвращаем пользователя на главное меню вместо тупика "Отменено"
        main_text, main_kb = _build_main_menu(user)
        try:
            await query.edit_message_text(
                main_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=main_kb,
            )
        except TelegramError:
            try:
                await query.message.delete()
            except TelegramError:
                pass
            await ctx.bot.send_message(
                query.message.chat_id,
                main_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=main_kb,
            )
        return

    if data == "info":
        info: VideoInfo = ctx.user_data.get(KEY_VIDEO_INFO)
        if not info:
            await query.answer("❌ Сессия истекла. Отправьте ссылку заново.", show_alert=True)
            return
        await _show_info(query, info, url=ctx.user_data.get(KEY_PENDING_URL, ""))
        return

    if data == "back_to_quality":
        await _handle_back_to_quality(query, ctx)
        return

    # Выбор: видео или плейлист для смешанного URL
    if data.startswith("resolve:"):
        await _handle_resolve_callback(query, ctx, data)
        return

    if data == "clear_history":
        deleted = db.clear_user_history(user.id)
        await query.answer(f"🗑 Удалено записей: {deleted}", show_alert=True)
        main_text, main_kb = _build_main_menu(user)
        try:
            await query.edit_message_text(
                main_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=main_kb,
            )
        except TelegramError:
            pass
        return

    if data.startswith("deliver:"):
        await _handle_deliver_callback(query, ctx, data)
    elif data.startswith("dl:"):
        await _handle_download_callback(query, ctx, data)
    elif data.startswith("pl:"):
        await _handle_playlist_callback(query, ctx, data)


async def _handle_menu_callback(query, ctx, data: str):
    """Обрабатывает inline-кнопки главного меню /start."""
    action = data.split(":", 1)[1]
    user = query.from_user

    if action == "help":
        is_adm = db.is_admin(user.id)
        text = (
            "📖 <b>Справка по боту</b>\n\n"
            "<b>Как использовать:</b>\n"
            "1. Отправьте ссылку на видео\n"
            "2. Выберите качество или аудио\n"
            "3. Дождитесь файла\n\n"
            + SUPPORTED_SITES_TEXT +
            "\n\n⚠️ <b>Ограничения:</b>\n"
            f"• Максимальный размер: {config.MAX_FILE_SIZE_MB} МБ\n\n"
            "<b>Команды:</b>\n"
            "/history, /status, /cancel"
        )
        if is_adm:
            text += "\n/pending, /users, /approve, /deny, /ban, /unban, /addadmin, /stats"
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="menu:back"),
            ]]),
        )

    elif action == "history":
        rows = db.get_user_history(user.id, limit=10)
        if not rows:
            text = "📭 История загрузок пуста."
            buttons = [[InlineKeyboardButton("« Назад", callback_data="menu:back")]]
        else:
            lines = ["📜 <b>Последние загрузки:</b>\n"]
            for i, row in enumerate(rows, 1):
                icon = {"done": "✅", "error": "❌", "pending": "⏳"}.get(row["status"], "•")
                title = _esc((row["title"] or row["url"])[:50])  # MEDIUM-3: escape HTML
                lines.append(f"{i}. {icon} {title}")
            text = "\n".join(lines)
            buttons = [
                [InlineKeyboardButton("🗑 Очистить историю", callback_data="clear_history")],
                [InlineKeyboardButton("« Назад", callback_data="menu:back")],
            ]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif action == "status":
        stats = db.get_global_stats()
        disk = shutil.disk_usage(str(config.DOWNLOAD_DIR))
        text = (
            "📊 <b>Статус бота</b>\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"📥 Всего загрузок: {stats['total_downloads']}\n"
            f"💾 Отправлено: {_human_size(stats['total_size_bytes'])}\n"
            f"⏳ Ожидают: {stats['pending_requests']}\n\n"
            f"🖥 Диск: {_human_size(disk.free)} свободно / {_human_size(disk.total)}"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="menu:back"),
            ]]),
        )

    elif action == "back":
        text, keyboard = _build_main_menu(query.from_user)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )

    elif action == "pending":
        if not db.is_admin(user.id):
            await query.answer("🚫 Только для администраторов.", show_alert=True)
            return
        rows = db.get_pending_users()
        if not rows:
            text = "✅ Заявок на доступ нет."
        else:
            lines = ["⏳ <b>Ожидают одобрения:</b>\n"]
            for r in rows:
                uname = f"@{r['username']}" if r['username'] else _esc(r['full_name'])  # LOW-4
                lines.append(f"• {uname} <code>{r['user_id']}</code>")
            text = "\n".join(lines) + "\n\nИспользуйте /pending для одобрения."
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data="menu:back")]]),
        )

    elif action == "users":
        if not db.is_admin(user.id):
            await query.answer("🚫 Только для администраторов.", show_alert=True)
            return
        rows = db.list_users(approved=True)
        if not rows:
            text = "Нет одобренных пользователей."
        else:
            lines = [f"👥 <b>Пользователи ({len(rows)}):</b>\n"]
            for r in rows[:20]:  # ограничиваем 20
                uname = f"@{r['username']}" if r['username'] else r['full_name']
                admin_tag = " 👑" if r['is_admin'] else ""
                lines.append(f"• {uname} <code>{r['user_id']}</code>{admin_tag}")
            text = "\n".join(lines)
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data="menu:back")]]),
        )

    elif action == "stats":
        if not db.is_admin(user.id):
            await query.answer("🚫 Только для администраторов.", show_alert=True)
            return
        stats = db.get_global_stats()
        disk = shutil.disk_usage(str(config.DOWNLOAD_DIR))
        text = (
            "📊 <b>Глобальная статистика</b>\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"⏳ Ожидают: {stats['pending_requests']}\n"
            f"📥 Загрузок: {stats['total_downloads']}\n"
            f"💾 Отправлено: {_human_size(stats['total_size_bytes'])}\n\n"
            f"🖥 Диск: {_human_size(disk.free)} свободно / {_human_size(disk.total)}"
        )
        await query.edit_message_text(
            text, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data="menu:back")]]),
        )


async def _handle_resolve_callback(query, ctx, data: str):
    """Обрабатывает выбор 'видео' или 'плейлист' для смешанного URL."""
    choice = data.split(":", 1)[1]

    if choice == "video":
        url = ctx.user_data.get(KEY_PENDING_URL)  # clean URL (без list=)
    else:
        url = ctx.user_data.get(KEY_ORIG_URL)  # оригинальный URL (с list=)

    # Очищаем временный оригинальный URL — он больше не нужен
    ctx.user_data.pop(KEY_ORIG_URL, None)

    if not url:
        await query.edit_message_text("❌ Сессия истекла. Отправьте ссылку заново.")
        return

    await query.edit_message_text("🔍 Получаю информацию о видео…")
    await _fetch_and_show_menu(url, query.message, ctx)


async def _show_info(query, info: VideoInfo, url: str = ""):
    text = (
        f"ℹ️ <b>{_esc(info.title)}</b>\n\n"
        f"👤 Автор: {_esc(info.uploader or '—')}\n"
        f"⏱ Длительность: {info.duration_str}\n"
        f"👁 Просмотры: {info.views_str}\n"
        f"🌐 Платформа: {_esc(info.extractor or '—')}\n"
    )
    if info.like_count:
        text += f"👍 Лайки: {_fmt_num(info.like_count)}\n"
    if info.description:
        text += f"\n📝 {_esc(info.description[:400])}…"
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("« Назад к выбору качества", callback_data="back_to_quality")]])
    try:
        await query.edit_message_caption(text, parse_mode=ParseMode.HTML, reply_markup=back_kb)
    except TelegramError:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_kb)
    # Сбрасываем таймер 2-часовой очистки при активном использовании
    if url:
        try:
            db.save_session(query.message.chat_id, query.message.message_id, url, _serialize_video_info(info))
        except Exception:
            pass


async def _handle_back_to_quality(query, ctx: ContextTypes.DEFAULT_TYPE):
    """Возврат к меню выбора качества из экрана 'Подробнее'."""
    info: VideoInfo = ctx.user_data.get(KEY_VIDEO_INFO)
    if not info:
        session = db.get_session(query.message.chat_id, query.message.message_id)
        if session:
            try:
                info = _deserialize_video_info(session["video_info_json"])
                ctx.user_data[KEY_VIDEO_INFO] = info
                ctx.user_data[KEY_PENDING_URL] = session["url"]
            except Exception as e:
                logger.warning("restore_session (back) failed: %s", e)
    if not info:
        await query.answer("❌ Сессия истекла. Отправьте ссылку заново.", show_alert=True)
        return
    caption, keyboard = _build_quality_menu(info)
    try:
        await query.edit_message_caption(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except TelegramError:
        try:
            await query.edit_message_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except TelegramError:
            pass
    # Сбрасываем таймер 2-часовой очистки при активном использовании
    url = ctx.user_data.get(KEY_PENDING_URL, "")
    if url:
        try:
            db.save_session(query.message.chat_id, query.message.message_id, url, _serialize_video_info(info))
        except Exception:
            pass


async def _handle_admin_approval(query, ctx, data: str):
    if not db.is_admin(query.from_user.id):
        await query.answer("Нет прав.", show_alert=True)
        return

    action, uid_str = data.split(":", 1)
    try:
        target_id = int(uid_str)
    except ValueError:
        await query.answer("Некорректный ID пользователя.", show_alert=True)
        return

    if action == "approve":
        ok = db.approve_user(target_id, query.from_user.id)
        if ok:
            await query.edit_message_text(f"✅ Пользователь {target_id} одобрен.")
            try:
                await ctx.bot.send_message(
                    target_id,
                    "✅ Ваша заявка одобрена! Отправьте /start для начала."
                )
            except TelegramError:
                pass
        else:
            await query.answer("Пользователь не найден.", show_alert=True)
    else:
        db.ban_user(target_id)
        await query.edit_message_text(f"🚫 Пользователь {target_id} отклонён/заблокирован.")
        try:
            await ctx.bot.send_message(target_id, "❌ Ваша заявка на доступ отклонена.")
        except TelegramError:
            pass


def _estimate_download_size(fmt_obj: Optional[FormatInfo], duration: int, audio_only: bool) -> Optional[int]:
    """Оценивает итоговый размер файла ДО загрузки.

    Возвращает None если нет данных для оценки.
    При audio_only оценивает только аудио (~192 kbps MP3).
    При video оценивает видео + аудио-дорожку (~128 kbps).
    """
    if audio_only:
        # MP3 192 kbps
        if duration:
            return int(192 * 1000 / 8 * duration)
        return None

    if not fmt_obj:
        return None

    # Точный размер известен
    if fmt_obj.filesize:
        base = fmt_obj.filesize
    elif fmt_obj.tbr and duration:
        base = int(fmt_obj.tbr * 1000 / 8 * duration)
    else:
        return None

    # Прибавляем примерный размер аудио-дорожки (128 kbps * duration)
    audio_overhead = int(128 * 1000 / 8 * duration) if duration else 0
    # Добавляем 10% запас на контейнер и метаданные
    return int((base + audio_overhead) * 1.1)


async def _handle_download_callback(query, ctx, data: str):
    # data: dl:<type>:<format_id>   type: v=video, a=audio, s=subtitle
    parts = data.split(":", 2)
    dl_type = parts[1]
    format_id = parts[2]

    sem: asyncio.Semaphore = ctx.bot_data.get("_download_sem")

    # Сначала ищем сессию в БД по message_id — это корректно при групповой загрузке,
    # когда каждое видео имеет своё сообщение-меню. ctx.user_data содержит данные
    # только последнего видео и ведёт к ошибке при выборе качества для предыдущих.
    info: VideoInfo = None
    url: str = None
    session = db.get_session(query.message.chat_id, query.message.message_id)
    if session:
        try:
            info = _deserialize_video_info(session["video_info_json"])
            url = session["url"]
        except Exception as e:
            logger.warning("restore_session failed: %s", e)
    # Фолбэк на user_data (одиночная ссылка или отсутствие сессии в БД)
    if not info or not url:
        info = ctx.user_data.get(KEY_VIDEO_INFO)
        url = ctx.user_data.get(KEY_PENDING_URL)
    if not info or not url:
        await query.answer("❌ Сессия истекла. Отправьте ссылку заново.", show_alert=True)
        return
    # Обновляем user_data для совместимости с остальным кодом
    ctx.user_data[KEY_VIDEO_INFO] = info
    ctx.user_data[KEY_PENDING_URL] = url

    # Сохраняем до возможного удаления сообщения (при фото-меню)
    _session_chat_id = query.message.chat_id
    _session_msg_id  = query.message.message_id

    # Меню выбора качества трансформируется в сообщение прогресса —
    # сбрасываем ключ, чтобы следующий URL не пытался удалить уже изменившееся сообщение.
    ctx.user_data.pop(KEY_QUALITY_MSG, None)

    user = query.from_user
    dl_id = db.add_download(user.id, url)
    ctx.user_data[KEY_DOWNLOAD_ID] = dl_id

    # CRITICAL-3: validate format_id against known formats (allowlist)
    if dl_type == "v" and format_id not in ("best",):
        valid_fids = {f.format_id for f in info.formats}
        if format_id not in valid_fids:
            logger.warning(
                "Invalid format_id %r from user %s (not in offered formats)",
                format_id, query.from_user.id,
            )
            await query.answer("❌ Неверный формат. Отправьте ссылку заново.", show_alert=True)
            return

    audio_only = dl_type in ("a", "ao", "aw")
    audio_format = "opus" if dl_type == "ao" else "wav" if dl_type == "aw" else "mp3"
    subtitle_lang = format_id if dl_type == "s" else None
    if dl_type == "s":
        format_id = "best"

    if dl_type == "a":
        quality_label = "Аудио MP3"
        fmt_obj = None
    elif dl_type == "ao":
        quality_label = "Аудио OPUS"
        fmt_obj = None
    elif dl_type == "aw":
        quality_label = "Аудио WAV"
        fmt_obj = None
    elif dl_type == "s":
        quality_label = f"Субтитры ({subtitle_lang})"
        fmt_obj = None
    elif format_id == "best":
        quality_label = "Лучшее качество"
        fmt_obj = None
    else:
        fmt_obj = next((f for f in info.formats if f.format_id == format_id), None)
        quality_label = f"Видео {fmt_obj.resolution}" if fmt_obj else "Лучшее качество"

    # Проверяем размер файла ДО начала загрузки (экономит трафик и время).
    # Для форматов без точного filesize оцениваем по TBR × длительность.
    _est_size = _estimate_download_size(fmt_obj, info.duration or 0, audio_only)
    if _est_size and _est_size > config.MAX_FILE_SIZE_BYTES:
        _known = fmt_obj and fmt_obj.filesize
        _label = _human_size(_est_size) + ("" if _known else " (оценка)")
        # ВАЖНО: query.answer() уже вызван в handle_callback → второй вызов
        # show_alert=True Telegram игнорирует. Показываем ошибку редактированием.
        _caption, _keyboard = _build_quality_menu(info)
        try:
            await query.edit_message_text(
                f"⚠️ <b>Файл слишком большой</b>: {_label}\n"
                f"Лимит: <b>{config.MAX_FILE_SIZE_MB} МБ</b>\n"
                f"Выберите более низкое качество:\n\n{_caption}",
                parse_mode=ParseMode.HTML,
                reply_markup=_keyboard,
            )
        except TelegramError:
            pass
        db.update_download(dl_id, status="error", error=f"pre-check: too large ~{_est_size}")
        return

    db.update_download(dl_id, title=info.title, format_id=format_id, quality=quality_label, status="downloading")

    cancel_flag = [False]
    ctx.user_data["cancel_flag"] = cancel_flag
    # Сохраняем текущую задачу — нужно для надёжной отмены через task.cancel()
    # (при aria2c progress_hook вызывается редко, поэтому cancel_flag недостаточно)
    ctx.user_data["_download_task"] = asyncio.current_task()
    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Отменить", callback_data="cancel")]])

    try:
        status_msg = await query.edit_message_text(
            f"⬇️ Загружаю: <b>{_esc(info.title)}</b>\n"
            f"Качество: {quality_label}\n\n"
            "⏳ Пожалуйста, подождите…",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_kb,
        )
    except TelegramError:
        # Фото-сообщение нельзя отредактировать в текст — удаляем и отправляем новое
        try:
            await query.message.delete()
        except TelegramError:
            pass
        status_msg = await ctx.bot.send_message(
            query.message.chat_id,
            f"⬇️ Загружаю: <b>{_esc(info.title)}</b>\n"
            f"Качество: {quality_label}\n\n"
            "⏳ Пожалуйста, подождите…",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_kb,
        )

    async def _on_progress(tracker: ProgressTracker) -> None:
        if cancel_flag[0]:
            return
        if tracker.status == "finished":
            # Загрузка потока завершена — идёт пост-обработка (FFmpeg).
            # Для аудио: конвертация в MP3.
            # Для видео: слияние видео+аудио потоков (fired дважды — после каждого потока).
            if not audio_only:
                proc_str = "🔄 Обрабатываю (FFmpeg)..."
            elif audio_format == "opus":
                proc_str = "🔄 Извлекаю OPUS..."
            elif audio_format == "wav":
                proc_str = "🔄 Конвертирую в WAV..."
            else:
                proc_str = "🔄 Конвертирую в MP3..."
            try:
                await status_msg.edit_text(
                    f"⬇️ Загружаю: <b>{_esc(info.title)}</b>\n"
                    f"Качество: {quality_label}\n\n"
                    f"{proc_str}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=cancel_kb,
                )
            except TelegramError:
                pass
            return
        speed_str = f"{tracker.speed / 1_048_576:.1f} МБ/с" if tracker.speed else "—"
        if tracker.eta:
            m, s = divmod(int(tracker.eta), 60)
            eta_str = f"{m}м {s:02d}с" if m else f"{s}с"
        else:
            eta_str = "—"
        if tracker.total:
            pct = tracker.downloaded / tracker.total * 100
            dl_str = f"⏳ {pct:.1f}% • {speed_str} • ETA: {eta_str}"
        else:
            # Размер неизвестен (HLS/DASH фрагменты, aria2c) — показываем скачанное
            dl_str = f"⏳ {_human_size(tracker.downloaded)} • {speed_str}"
            if eta_str != "—":
                dl_str += f" • ETA: {eta_str}"
        try:
            await status_msg.edit_text(
                f"⬇️ Загружаю: <b>{_esc(info.title)}</b>\n"
                f"Качество: {quality_label}\n\n"
                f"{dl_str}",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_kb,
            )
        except TelegramError:
            pass

    await ctx.bot.send_chat_action(query.message.chat_id, ChatAction.UPLOAD_DOCUMENT)

    # Перепривязываем сессию к текущему сообщению (если меню было фото и удалено)
    try:
        db.save_session(status_msg.chat_id, status_msg.message_id, url, _serialize_video_info(info))
        if _session_msg_id != status_msg.message_id:
            db.delete_session(_session_chat_id, _session_msg_id)
    except Exception as e:
        logger.warning("re-key session failed: %s", e)

    tmp_dir = config.DOWNLOAD_DIR / f"user_{user.id}" / f"dl_{dl_id}"
    # MEDIUM-4: ensure tmp_dir is inside DOWNLOAD_DIR before use
    try:
        tmp_dir.resolve().relative_to(config.DOWNLOAD_DIR.resolve())
    except ValueError:
        logger.error("Download dir path traversal: %s is outside %s", tmp_dir, config.DOWNLOAD_DIR)
        await query.answer("❌ Внутренняя ошибка.", show_alert=True)
        return
    # Если все слоты заняты — уведомляем пользователя и ждём в очереди.
    _sem = sem or asyncio.Semaphore(1)
    _need_queue = sem is not None and getattr(sem, '_value', 1) == 0
    if _need_queue:
        try:
            await status_msg.edit_text(
                f"⏳ <b>В очереди загрузок</b>\n"
                f"{_esc(info.title)}\n\n"
                f"Все {config.MAX_CONCURRENT_DOWNLOADS} слота заняты — загрузка начнётся автоматически.",
                parse_mode=ParseMode.HTML,
            )
        except TelegramError:
            pass

    try:
        async with _sem:
            # Если ждали в очереди — восстанавливаем статус "загружаю"
            if _need_queue:
                try:
                    await status_msg.edit_text(
                        f"⬇️ Загружаю: <b>{_esc(info.title)}</b>\n"
                        f"Качество: {quality_label}\n\n"
                        "⏳ Пожалуйста, подождите…",
                        parse_mode=ParseMode.HTML,
                        reply_markup=cancel_kb,
                    )
                except TelegramError:
                    pass
            try:
                result: DownloadResult = await download_video(
                    url=url,
                    format_id=format_id,
                    output_dir=tmp_dir,
                    audio_only=audio_only,
                    audio_format=audio_format,
                    subtitle_lang=subtitle_lang,
                    progress_callback=_on_progress,
                    cancel_flag=cancel_flag,
                )

                ctx.user_data.pop("cancel_flag", None)
                ctx.user_data.pop("_download_task", None)

                if not result.success:
                    _caption, _keyboard = _build_quality_menu(info)
                    if result.error == "CANCELLED":
                        # Отмена через _cancel_hook — возвращаем меню качества
                        try:
                            await status_msg.edit_text(_caption, parse_mode=ParseMode.HTML, reply_markup=_keyboard)
                        except TelegramError:
                            pass
                        return
                    db.update_download(dl_id, status="error", error=result.error)
                    # Специальное сообщение для превышения лимита размера файла
                    if result.error and result.error.startswith("File too large"):
                        # Парсим "File too large: 12.3 GB (max 10.0 GB)" → берём размер
                        actual_size = result.error.replace("File too large: ", "").split(" (")[0]
                        err_text = (
                            f"⚠️ <b>Файл слишком большой</b>\n\n"
                            f"Скачанный файл <b>{actual_size}</b> превысил лимит "
                            f"<b>{config.MAX_FILE_SIZE_MB} МБ</b>.\n\n"
                            f"Выберите более низкое качество:\n\n{_caption}"
                        )
                    elif result.error and _login_required_text(result.error):
                        err_text = _login_required_text(result.error)
                    else:
                        err_text = f"❌ Ошибка: <code>{_esc(result.error[:300])}</code>\n\n{_caption}"
                    try:
                        await status_msg.edit_text(err_text, parse_mode=ParseMode.HTML, reply_markup=_keyboard)
                        _schedule_delete(ctx.bot, status_msg.chat_id, status_msg.message_id)
                    except TelegramError:
                        pass
                    return

                db.update_download(dl_id, status="done", file_size=result.file_size)

                _has_fileserver = config.PUBLIC_BASE_URL or config.DIRECT_BASE_URL
                if _has_fileserver:
                    # Файловый сервер включён — предлагаем выбор доставки
                    try:
                        fs_token = fileserver.move_and_register(
                            result.file_path, config.FILE_TTL_SECONDS
                        )
                        ctx.user_data["_pending_delivery"] = {
                            "token": fs_token,
                            "dl_id": dl_id,
                            "info": info,
                            "url": url,
                            "file_size": result.file_size,
                            "title": result.title or info.title,
                        }
                        ttl_h = max(1, config.FILE_TTL_SECONDS // 3600)
                        deliver_buttons = [[
                            InlineKeyboardButton(
                                "📤 Отправить в Telegram",
                                callback_data="deliver:tg",
                            ),
                        ]]
                        if config.PUBLIC_BASE_URL:
                            deliver_buttons.append([InlineKeyboardButton(
                                f"🔗 Ссылка через Cloudflare ({ttl_h}ч)",
                                callback_data="deliver:link",
                            )])
                        if config.DIRECT_BASE_URL:
                            deliver_buttons.append([InlineKeyboardButton(
                                f"🌐 Прямая ссылка с сервера ({ttl_h}ч)",
                                callback_data="deliver:direct",
                            )])
                        if config.RELAY_BASE_URL:
                            deliver_buttons.append([InlineKeyboardButton(
                                f"🔄 Relay-ссылка ({ttl_h}ч)",
                                callback_data="deliver:relay",
                            )])
                        await status_msg.edit_text(
                            f"✅ <b>{_esc(result.title or info.title)}</b>\n"
                            f"📦 {_human_size(result.file_size)}\n\n"
                            "Как получить файл?",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(deliver_buttons),
                        )
                    except Exception as e:
                        logger.error("fileserver.move_and_register failed: %s", e)
                        # Фолбэк: отправляем через Telegram напрямую
                        await ctx.bot.send_chat_action(query.message.chat_id, ChatAction.UPLOAD_DOCUMENT)
                        await _deliver_file_with_progress(
                            query.message.chat_id, result, ctx.bot, status_msg
                        )
                        _caption, _keyboard = _build_quality_menu(info)
                        try:
                            await status_msg.edit_text(
                                f"✅ <b>{_esc(result.title or info.title)}</b>  {_human_size(result.file_size)}\n\n"
                                + _caption,
                                parse_mode=ParseMode.HTML,
                                reply_markup=_keyboard,
                            )
                            _schedule_delete(ctx.bot, status_msg.chat_id, status_msg.message_id)
                        except TelegramError:
                            pass
                else:
                    # Прямая отправка в Telegram
                    await ctx.bot.send_chat_action(query.message.chat_id, ChatAction.UPLOAD_DOCUMENT)
                    await _deliver_file_with_progress(
                        query.message.chat_id, result, ctx.bot, status_msg
                    )
                    _caption, _keyboard = _build_quality_menu(info)
                    try:
                        await status_msg.edit_text(
                            f"✅ <b>{_esc(result.title or info.title)}</b>  {_human_size(result.file_size)}\n\n"
                            + _caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=_keyboard,
                        )
                        _schedule_delete(ctx.bot, status_msg.chat_id, status_msg.message_id)
                    except TelegramError:
                        pass
                    try:
                        db.save_session(
                            status_msg.chat_id, status_msg.message_id,
                            url, _serialize_video_info(info),
                        )
                    except Exception:
                        pass

            except asyncio.CancelledError:
                raise  # Поднимаем наверх — будет поймано во внешнем try

            except Exception as e:
                logger.error("Download error: %s\n%s", e, traceback.format_exc())
                db.update_download(dl_id, status="error", error=str(e))
                _caption, _keyboard = _build_quality_menu(info)
                try:
                    await status_msg.edit_text(
                        f"❌ Неожиданная ошибка:\n<code>{_esc(str(e)[:200])}</code>\n\n{_caption}",
                        parse_mode=ParseMode.HTML,
                        reply_markup=_keyboard,
                    )
                except TelegramError:
                    pass
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                ctx.user_data.pop("cancel_flag", None)
                ctx.user_data.pop("_download_task", None)
                # KEY_VIDEO_INFO и KEY_PENDING_URL не очищаем — пользователь может
                # скачать другой формат без повторной отправки ссылки.
                # Сессия удаляется только при явной отмене (❌ Отмена).

    except asyncio.CancelledError:
        # Не должно возникать при нормальной работе (task.cancel() больше не вызывается).
        # Оставляем как safety-net на случай внешней отмены задачи (например, shutdown бота).
        db.update_download(dl_id, status="error", error="CANCELLED")
        raise


async def _notify_link_expiry(bot: Bot, chat_id: int, title: str, info_url: str, token: str, delay: int) -> None:
    """Уведомляет пользователя за 10 минут до истечения ссылки файлового сервера."""
    await asyncio.sleep(delay)
    # Проверяем, что файл ещё существует (не был скачан досрочно)
    if fileserver.get_entry(token):
        try:
            await bot.send_message(
                chat_id,
                f"⏰ <b>Ссылка истекает через 10 минут:</b>\n"
                f"<a href='{info_url}'>{_esc(title[:60])}</a>\n\n"
                "Успейте скачать!",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except TelegramError:
            pass


async def _handle_deliver_callback(query, ctx, data: str):
    """Обрабатывает выбор способа доставки файла: Telegram, ссылка Cloudflare, прямая с сервера или relay."""
    action = data.split(":", 1)[1]  # "tg", "link", "direct" или "relay"
    pd = ctx.user_data.get("_pending_delivery")

    if not pd:
        await query.answer(
            "❌ Сессия доставки истекла. Скачайте файл заново.",
            show_alert=True,
        )
        try:
            await query.edit_message_text("❌ Сессия доставки истекла. Отправьте ссылку заново.")
        except TelegramError:
            pass
        return

    token: str = pd["token"]
    dl_id: int = pd["dl_id"]
    info: VideoInfo = pd["info"]
    url: str = pd.get("url", "")
    file_size: int = pd.get("file_size", 0)
    title: str = pd.get("title", "")

    entry = fileserver.get_entry(token)

    if action in ("link", "direct", "relay"):
        # ── Доставка через ссылку файлового сервера ──────────────────────────────
        if not entry:
            await query.answer("❌ Файл недоступен (истёк TTL). Скачайте заново.", show_alert=True)
            ctx.user_data.pop("_pending_delivery", None)
            return

        ctx.user_data.pop("_pending_delivery", None)

        base = (
            config.DIRECT_BASE_URL if action == "direct" else
            config.RELAY_BASE_URL  if action == "relay"  else
            config.PUBLIC_BASE_URL
        )
        info_url = f"{base}/info/{token}"
        ttl_h = max(1, config.FILE_TTL_SECONDS // 3600)
        _caption, _keyboard = _build_quality_menu(info)

        via_label = "сервер" if action == "direct" else "relay" if action == "relay" else "Cloudflare"

        # Планируем уведомление за 10 мин до истечения TTL
        notify_delay = config.FILE_TTL_SECONDS - 600
        if notify_delay > 60:
            asyncio.create_task(_notify_link_expiry(
                ctx.bot, query.message.chat_id, title, info_url, token, notify_delay
            ))

        try:
            await query.edit_message_text(
                f"🔗 <b>Ссылка для скачивания ({via_label}):</b>\n"
                f"<a href='{info_url}'>{info_url}</a>\n\n"
                f"📦 {_human_size(file_size)}\n"
                f"⏱ Действует <b>{ttl_h} ч</b> (удаляется после первого скачивания)\n\n"
                + _caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=_keyboard,
            )
            _schedule_delete(ctx.bot, query.message.chat_id, query.message.message_id)
        except TelegramError:
            pass
        if url:
            try:
                db.save_session(
                    query.message.chat_id, query.message.message_id,
                    url, _serialize_video_info(info),
                )
            except Exception:
                pass
        return

    if action == "tg":
        # ── Доставка через Telegram ──────────────────────────────────────────────
        if not entry or not entry.path.exists():
            await query.answer("❌ Файл недоступен (истёк TTL). Скачайте заново.", show_alert=True)
            ctx.user_data.pop("_pending_delivery", None)
            return

        # Снимаем с учёта файлового сервера ДО отправки (чтобы TTL-cleanup не удалил файл)
        fileserver.unregister(token, delete_file=False)
        ctx.user_data.pop("_pending_delivery", None)

        result = DownloadResult(
            success=True,
            file_path=entry.path,
            title=title,
            file_size=entry.file_size,
        )

        try:
            await query.edit_message_text(
                f"📤 Отправляю <b>{_esc(title)}</b> ({_human_size(entry.file_size)})…",
                parse_mode=ParseMode.HTML,
            )
        except TelegramError:
            pass

        await ctx.bot.send_chat_action(query.message.chat_id, ChatAction.UPLOAD_DOCUMENT)
        try:
            await _deliver_file_with_progress(query.message.chat_id, result, ctx.bot, query.message)
        except Exception as e:
            logger.error("Telegram delivery failed, cleaning up: %s", e)
            entry.path.unlink(missing_ok=True)
            try:
                entry.path.parent.rmdir()
            except OSError:
                pass
            await query.answer("❌ Не удалось отправить файл. Скачайте заново.", show_alert=True)
            return

        # Удаляем директорию файлового сервера (файл удалён _deliver_file)
        try:
            entry.path.parent.rmdir()
        except OSError:
            pass

        db.update_download(dl_id, status="done")
        _caption, _keyboard = _build_quality_menu(info)
        try:
            await query.message.edit_text(
                f"✅ <b>{_esc(title)}</b>  {_human_size(entry.file_size)}\n\n" + _caption,
                parse_mode=ParseMode.HTML,
                reply_markup=_keyboard,
            )
            _schedule_delete(ctx.bot, query.message.chat_id, query.message.message_id)
        except TelegramError:
            pass
        if url:
            try:
                db.save_session(
                    query.message.chat_id, query.message.message_id,
                    url, _serialize_video_info(info),
                )
            except Exception:
                pass



async def _handle_playlist_callback(query, ctx, data: str):
    parts = data.split(":")
    try:
        max_items = int(parts[1])
        quality = parts[2]
    except (IndexError, ValueError):
        await query.answer("❌ Некорректный запрос.", show_alert=True)
        return
    audio_only = quality == "audio"

    info: VideoInfo = ctx.user_data.get(KEY_VIDEO_INFO)
    url = ctx.user_data.get(KEY_PENDING_URL)
    if not info or not url:
        await query.edit_message_text("❌ Сессия истекла.")
        return

    user = query.from_user
    dl_id = db.add_download(user.id, url)

    await query.edit_message_text(
        f"⬇️ Загружаю плейлист: <b>{_esc(info.title)}</b>\n"
        f"До {max_items} видео\n\n⏳ Это может занять несколько минут…",
        parse_mode=ParseMode.HTML,
    )

    tmp_dir = config.DOWNLOAD_DIR / f"user_{user.id}" / f"pl_{dl_id}"
    try:
        from downloader import download_playlist
        results = await download_playlist(
            url=url,
            format_id="bestaudio" if audio_only else "best",
            output_dir=tmp_dir,
            max_items=max_items,
        )

        sent = 0
        skipped = 0
        fs_links: list[tuple[str, str, str]] = []  # (title, size_str, url)

        for r in results:
            if r.success and r.file_path and r.file_path.exists():
                if r.file_size <= config.MAX_FILE_SIZE_BYTES:
                    if config.PUBLIC_BASE_URL or config.DIRECT_BASE_URL:
                        # Файловый сервер включён — регистрируем файл и собираем ссылки.
                        # move_and_register перемещает файл из tmp_dir → папку fileserver,
                        # поэтому shutil.rmtree в finally не затронет его.
                        _pl_base = config.DIRECT_BASE_URL or config.PUBLIC_BASE_URL
                        try:
                            token = fileserver.move_and_register(
                                r.file_path, config.FILE_TTL_SECONDS
                            )
                            info_url = f"{_pl_base}/info/{token}"
                            fs_links.append((
                                r.title or r.file_path.stem,
                                _human_size(r.file_size),
                                info_url,
                            ))
                        except Exception as fs_err:
                            logger.warning("fileserver playlist item failed: %s — fallback to TG", fs_err)
                            await _deliver_file(query.message.chat_id, r, ctx.bot)
                    else:
                        await _deliver_file(query.message.chat_id, r, ctx.bot)
                    sent += 1
                    await asyncio.sleep(1)
                else:
                    skipped += 1

        # Отправляем все ссылки одним сообщением (только в режиме файлового сервера)
        if fs_links:
            ttl_h = max(1, config.FILE_TTL_SECONDS // 3600)
            lines = [f"🔗 <b>Ссылки для скачивания</b> (действуют {ttl_h} ч):\n"]
            for i, (title, size_str, link_url) in enumerate(fs_links, 1):
                lines.append(f"{i}. <a href='{link_url}'>{_esc(title[:60])}</a>  {size_str}")
            await ctx.bot.send_message(
                query.message.chat_id,
                "\n".join(lines),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

        db.update_download(dl_id, title=info.title, status="done")
        summary = f"✅ Плейлист готов. Отправлено: {sent}/{len(results)}"
        if skipped:
            summary += f" (пропущено {skipped} — превышен лимит размера)"
        await ctx.bot.send_message(query.message.chat_id, summary)

    except Exception as e:
        logger.error("Playlist error: %s", e)
        db.update_download(dl_id, status="error", error=str(e))
        err_str = str(e)
        if "rate-limit" in err_str.lower() or "ratelimit" in err_str.lower() or "429" in err_str:
            user_msg = (
                "⚠️ <b>YouTube ограничил скорость запросов</b>\n\n"
                "YouTube временно заблокировал скачивание (rate limit).\n"
                "Попробуйте снова через 30–60 минут.\n\n"
                "<i>Совет: начните с меньшего количества видео (5 вместо 10).</i>"
            )
        else:
            user_msg = f"❌ Ошибка при загрузке плейлиста:\n<code>{_esc(err_str[:300])}</code>"
        await ctx.bot.send_message(query.message.chat_id, user_msg, parse_mode=ParseMode.HTML)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _deliver_file(chat_id: int, result: DownloadResult, bot: Bot, keep_file: bool = False):
    """Отправляет файл напрямую через Telegram Bot API.

    Используется в двух случаях:
    - Режим Telegram API (LOCAL_API_SERVER): локальный сервер читает файл
      с диска через общий том — нет ограничения 50 МБ, лимит до 2 ГБ.
    - Режим файлового сервера: вызывается только когда пользователь выбрал
      «📤 Отправить в Telegram» в _handle_deliver_callback() или при ошибке
      fileserver.move_and_register(). Регистрация в fileserver и выдача
      ссылок происходит в _handle_download_callback() / _handle_playlist_callback().
    """
    fp = result.file_path
    caption = f"📁 {fp.stem[:200]}  ({_human_size(result.file_size)})"
    is_audio = fp.suffix in (".mp3", ".ogg", ".m4a", ".flac", ".wav", ".opus")

    if config.LOCAL_API_SERVER:
        # local_mode=True: передаём абсолютный путь — локальный Bot API сервер
        # читает файл напрямую с диска через общий том /downloads.
        # Если API сервер не может stat() файл (например, права доступа),
        # падаем на чтение содержимого через bot-контейнер (fallback).
        fp_path = fp.resolve()
        try:
            if is_audio:
                await bot.send_audio(chat_id, audio=fp_path, caption=caption)
            else:
                await bot.send_document(chat_id, document=fp_path, caption=caption)
            if not keep_file:
                fp.unlink(missing_ok=True)
            return
        except TelegramError as exc:
            if "stat" not in str(exc).lower() and "bad request" not in str(exc).lower():
                raise
            logger.warning(
                "_deliver_file: local API stat() failed (%s), falling back to direct upload", exc
            )
            # Продолжаем ниже — читаем файл и шлём как multipart

    with fp.open("rb") as fh:
        if is_audio:
            await bot.send_audio(chat_id, audio=InputFile(fh, filename=fp.name), caption=caption)
        else:
            await bot.send_document(chat_id, document=InputFile(fh, filename=fp.name), caption=caption)

    if not keep_file:
        fp.unlink(missing_ok=True)


async def _deliver_file_with_progress(
    chat_id: int,
    result: DownloadResult,
    bot: Bot,
    status_msg: Message,
) -> None:
    """Обёртка над _deliver_file: каждые 3 с обновляет статусное сообщение
    с анимированным спиннером и таймером, чтобы пользователь видел прогресс."""
    total_str = _human_size(result.file_size)
    name_str = _esc((result.file_path.stem)[:80])

    stop_event = asyncio.Event()
    start_ts = time.monotonic()

    async def _spin() -> None:
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while not stop_event.is_set():
            elapsed = int(time.monotonic() - start_ts)
            m, s = divmod(elapsed, 60)
            t_str = f"{m}м {s:02d}с" if m else f"{s}с"
            try:
                await status_msg.edit_text(
                    f"📤 {frames[i % len(frames)]} Отправляю <b>{name_str}</b>\n"
                    f"📦 {total_str}  •  ⏱ {t_str}",
                    parse_mode=ParseMode.HTML,
                )
            except TelegramError:
                pass
            # Обновляем индикатор «загружает документ» (действует ~5 с)
            try:
                await bot.send_chat_action(chat_id, ChatAction.UPLOAD_DOCUMENT)
            except TelegramError:
                pass
            i += 1
            await asyncio.sleep(3.0)

    spin_task = asyncio.create_task(_spin())
    try:
        await _deliver_file(chat_id, result, bot)
    finally:
        stop_event.set()
        spin_task.cancel()
        try:
            await spin_task
        except (asyncio.CancelledError, Exception):
            pass


# ── Команды администратора ───────────────────────────────────────────────────────

@require_admin
async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = db.pending_users()
    if not rows:
        await update.message.reply_text("✅ Заявок на доступ нет.")
        return

    for row in rows:
        uname = f"@{row['username']}" if row['username'] else "(нет username)"
        text = (
            f"👤 <b>{_esc(row['full_name'])}</b> {uname}\n"
            f"🆔 <code>{row['user_id']}</code>\n"
            f"📅 Заявка: {row['created_at'][:16]}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{row['user_id']}"),
            InlineKeyboardButton("🚫 Отклонить", callback_data=f"deny:{row['user_id']}"),
        ]])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@require_admin
async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = db.list_users(approved=True)
    if not rows:
        await update.message.reply_text("Нет одобренных пользователей.")
        return

    lines = [f"👥 <b>Одобренные пользователи ({len(rows)}):</b>\n"]
    for r in rows:
        uname = f"@{r['username']}" if r['username'] else _esc(r['full_name'])  # LOW-4
        admin_tag = " 👑" if r['is_admin'] else ""
        lines.append(f"• {uname} <code>{r['user_id']}</code>{admin_tag}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@require_admin
async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _admin_user_action(update, ctx, "approve")


@require_admin
async def cmd_deny(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _admin_user_action(update, ctx, "deny")


@require_admin
async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _admin_user_action(update, ctx, "ban")


@require_admin
async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _admin_user_action(update, ctx, "unban")


@require_admin
async def cmd_addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _admin_user_action(update, ctx, "addadmin")


async def _admin_user_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE, action: str):
    args = ctx.args
    if not args:
        await update.message.reply_text(f"Использование: /{action} <user_id>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Некорректный user ID.")
        return

    if action == "approve":
        ok = db.approve_user(target_id, update.effective_user.id)
        msg = f"✅ Пользователь {target_id} одобрен." if ok else "Пользователь не найден."
        if ok:
            try:
                await ctx.bot.send_message(target_id, "✅ Ваш доступ одобрен! Отправьте /start.")
            except TelegramError:
                pass
    elif action == "deny":
        db.ban_user(target_id)
        msg = f"🚫 Пользователь {target_id} отклонён."
    elif action == "ban":
        ok = db.ban_user(target_id)
        msg = f"🔨 Пользователь {target_id} заблокирован." if ok else "Пользователь не найден."
    elif action == "unban":
        ok = db.unban_user(target_id)
        msg = f"✅ Пользователь {target_id} разблокирован." if ok else "Пользователь не найден."
    elif action == "addadmin":
        ok = db.set_admin(target_id, True)
        msg = f"👑 Пользователь {target_id} назначен администратором." if ok else "Пользователь не найден."
    else:
        msg = "Неизвестное действие."

    await update.message.reply_text(msg)


@require_admin
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    stats = db.get_global_stats()
    disk = shutil.disk_usage(str(config.DOWNLOAD_DIR))
    text = (
        "📊 <b>Глобальная статистика</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"⏳ Ожидают: {stats['pending_requests']}\n"
        f"📥 Загрузок: {stats['total_downloads']}\n"
        f"💾 Отправлено: {_human_size(stats['total_size_bytes'])}\n\n"
        f"🖥 Диск: {_human_size(disk.free)} свободно / {_human_size(disk.total)}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ── Обработчик ошибок ────────────────────────────────────────────────────────────

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception: %s", ctx.error, exc_info=ctx.error)


# ── Утилиты ──────────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_LOGIN_REQUIRED_HINTS = (
    "login required",
    "login_required",
    "cookies",
    "rate-limit reached",
    "rate limit reached",
    "not available",
    "requested content is not available",
    "private",
    "sign in",
)


def _login_required_text(err: str) -> str | None:
    """Если ошибка связана с авторизацией/куками — возвращает понятное сообщение,
    иначе None. Используется для Instagram, TikTok, Twitter/X и т.п."""
    low = err.lower()
    if not any(h in low for h in _LOGIN_REQUIRED_HINTS):
        return None
    return (
        "🔒 <b>Требуется авторизация</b>\n\n"
        "Этот контент недоступен без входа в аккаунт (Instagram, TikTok, Twitter/X и т.п.).\n\n"
        "<b>Как исправить:</b>\n"
        "1. Экспортируйте cookies из браузера в формате Netscape (расширение <i>Get cookies.txt</i>)\n"
        "2. Сохраните файл на сервер (например <code>/data/cookies.txt</code>)\n"
        "3. Добавьте в <code>.env</code>:\n"
        "   <code>COOKIES_FILE=/data/cookies.txt</code>\n"
        "4. Перезапустите бот: <code>docker compose up -d --build ytdlp-bot</code>"
    )


def _schedule_delete(bot, chat_id: int, message_id: int, delay: int = 0) -> None:
    """Планирует удаление сообщения через delay секунд (если AUTO_DELETE_SECONDS > 0)."""
    secs = delay or config.AUTO_DELETE_SECONDS
    if secs <= 0:
        return

    async def _do_delete():
        await asyncio.sleep(secs)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramError:
            pass  # уже удалено или нет прав

    asyncio.create_task(_do_delete())


def _human_size(n) -> str:
    if not n:
        return "0 Б"
    n = int(n)
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ПБ"


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}М"
    if n >= 1_000:
        return f"{n/1_000:.1f}К"
    return str(n)


# ── Периодическая очистка (asyncio, без APScheduler) ─────────────────────────────

async def _check_disk_alert(bot: Bot) -> bool:
    """Отправляет алерт администраторам если диск заполнен выше порога.

    Возвращает True если алерт был отправлен (для rate-limiting).
    """
    if not config.DISK_ALERT_THRESHOLD or not config.ADMIN_IDS:
        return False
    disk = shutil.disk_usage(str(config.DOWNLOAD_DIR))
    pct = disk.used / disk.total * 100
    if pct < config.DISK_ALERT_THRESHOLD:
        return False
    msg = (
        f"⚠️ <b>Диск заполнен на {pct:.0f}%</b>\n\n"
        f"Свободно: <b>{_human_size(disk.free)}</b> / {_human_size(disk.total)}\n"
        f"Порог алерта: {config.DISK_ALERT_THRESHOLD}%"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, msg, parse_mode=ParseMode.HTML)
        except TelegramError:
            pass
    return True


async def _cleanup_loop(bot: Bot) -> None:
    """Фоновый цикл: очистка каждый час. Запускается через post_init."""
    _last_disk_alert = 0.0
    while True:
        await asyncio.sleep(3600)
        try:
            await _cleanup_job()
        except Exception as e:
            logger.error("Ошибка очистки: %s", e)
        # Алерт о диске — не чаще 1 раза в 4 часа
        try:
            now = time.monotonic()
            if now - _last_disk_alert >= 14400:
                alerted = await _check_disk_alert(bot)
                if alerted:
                    _last_disk_alert = now
        except Exception as e:
            logger.error("Disk alert check failed: %s", e)


async def _post_init(application) -> None:
    application.bot_data["_download_sem"] = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
    task = asyncio.create_task(_cleanup_loop(application.bot))
    application.bot_data["_cleanup_task"] = task

    # Файловый HTTP-сервер: запускается если задан PUBLIC_BASE_URL или DIRECT_BASE_URL
    if config.PUBLIC_BASE_URL or config.DIRECT_BASE_URL:
        try:
            await fileserver.start(port=config.HTTP_PORT)
            urls = []
            if config.PUBLIC_BASE_URL:
                urls.append(f"туннель: {config.PUBLIC_BASE_URL}")
            if config.DIRECT_BASE_URL:
                urls.append(f"прямой IP: {config.DIRECT_BASE_URL}")
            logger.info(
                "Файловый сервер запущен: порт %d | %s",
                config.HTTP_PORT, " | ".join(urls),
            )
        except Exception as e:
            logger.error("Не удалось запустить файловый сервер: %s", e)
    else:
        logger.info("PUBLIC_BASE_URL и DIRECT_BASE_URL не заданы — файловый сервер отключён")

    # Устанавливаем список команд (видны при вводе "/" в Telegram)
    try:
        await application.bot.set_my_commands([
            BotCommand("start",   "Главное меню"),
            BotCommand("menu",    "Все команды"),
            BotCommand("history", "История загрузок"),
            BotCommand("status",  "Статус бота"),
            BotCommand("cancel",  "Отменить загрузку"),
            BotCommand("help",    "Справка"),
        ])
    except Exception as e:
        logger.warning("set_my_commands failed: %s", e)


async def _post_shutdown(application) -> None:
    task = application.bot_data.get("_cleanup_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    # Останавливаем файловый сервер
    if config.PUBLIC_BASE_URL or config.DIRECT_BASE_URL:
        await fileserver.stop()


async def _cleanup_job() -> None:
    """Каждый час: удаляет файлы старше FILE_TTL и данные."""
    removed = 0
    # Используем TTL из конфига (минимум 2 часа, чтобы не удалять активные загрузки)
    ttl = max(config.FILE_TTL_SECONDS, 7200)
    cutoff_ts = datetime.now().timestamp() - ttl

    if config.DOWNLOAD_DIR.exists():
        for item in config.DOWNLOAD_DIR.iterdir():
            # Не удаляем директорию fileserver — её TTL управляется модулем fileserver
            if item.name == "fileserver":
                continue
            try:
                if item.stat().st_mtime < cutoff_ts:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                pass
        # Удаляем пустые user_* директории
        for item in config.DOWNLOAD_DIR.iterdir():
            if item.name.startswith("user_") and item.is_dir():
                try:
                    item.rmdir()  # rmdir only succeeds if empty
                except OSError:
                    pass

    ttl_hours = max(1, ttl // 3600)
    old_sessions = db.cleanup_old_sessions(max_age_hours=ttl_hours)
    old_history  = db.cleanup_old_history(max_age_days=30)

    if removed_dirs or old_sessions or old_history:
        logger.info(
            "Очистка: файлов/папок=%d, сессий=%d, истории=%d",
            removed_dirs, old_sessions, old_history,
        )


# ── Запуск ───────────────────────────────────────────────────────────────────────

def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан!")
    if not config.ADMIN_IDS:
        raise RuntimeError("ADMIN_IDS не задан! (через запятую Telegram user ID)")

    # Маскируем токен в логах — должно быть первым делом
    _mask = _TokenMaskFilter(config.BOT_TOKEN)
    logging.root.addFilter(_mask)
    for _h in logging.root.handlers:
        _h.addFilter(_mask)

    db.init_db()
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Синхронизируем права администраторов с текущим ADMIN_IDS в .env
    # Если кто-то убран из ADMIN_IDS — теряет флаг is_admin в БД
    db.sync_admin_ids(config.ADMIN_IDS)

    # Авто-одобрение администраторов
    for admin_id in config.ADMIN_IDS:
        row = db.get_user(admin_id)
        if row is None:
            db.upsert_user(admin_id, "", "Admin")
        db.approve_user(admin_id, admin_id)
        db.set_admin(admin_id, True)

    from telegram.request import HTTPXRequest

    builder = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
    )

    # Локальный Bot API сервер снимает лимит 50 МБ → до 2 ГБ
    if config.LOCAL_API_SERVER:
        base_url      = f"{config.LOCAL_API_SERVER}/bot"
        base_file_url = f"{config.LOCAL_API_SERVER}/file/bot"
        # local_mode=True: PTB передаёт пути к файлам вместо их содержимого
        builder = builder.base_url(base_url).base_file_url(base_file_url).local_mode(True)
        logger.info("Используется локальный Bot API сервер: %s", config.LOCAL_API_SERVER)

    # Большие таймауты: файлы до 1.6 ГБ могут загружаться долго
    read_timeout  = 300.0   # 5 минут на чтение ответа при отправке большого файла
    write_timeout = 300.0   # 5 минут на запись (upload)

    if config.PROXY_URL:
        request = HTTPXRequest(
            proxy=config.PROXY_URL,
            connect_timeout=20.0,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
        )
        builder = builder.request(request).get_updates_request(HTTPXRequest(
            proxy=config.PROXY_URL,
            connect_timeout=20.0,
            read_timeout=30.0,
        ))
    else:
        builder = builder.request(HTTPXRequest(
            connect_timeout=20.0,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
        ))

    app = builder.build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Команды администратора
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("deny", cmd_deny))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # URL-сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    # Inline-кнопки
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Inline-режим (@botname <url>)
    app.add_handler(InlineQueryHandler(handle_inline_query))

    app.add_error_handler(error_handler)

    logger.info("Бот запускается… Администраторы: %s", config.ADMIN_IDS)

    if config.WEBHOOK_URL:
        logger.info("Webhook-режим: %s → порт %d", config.WEBHOOK_URL, config.WEBHOOK_PORT)
        # Используем безопасный путь вместо BOT_TOKEN — токен не попадёт в логи прокси
        import hashlib as _hashlib
        _webhook_path = _hashlib.sha256(config.BOT_TOKEN.encode()).hexdigest()[:24]
        app.run_webhook(
            listen="0.0.0.0",
            port=config.WEBHOOK_PORT,
            url_path=_webhook_path,
            webhook_url=f"{config.WEBHOOK_URL}/{_webhook_path}",
            secret_token=config.WEBHOOK_SECRET_TOKEN or None,
            drop_pending_updates=True,
        )
    else:
        app.run_polling(drop_pending_updates=True, bootstrap_retries=5)


if __name__ == "__main__":
    main()
