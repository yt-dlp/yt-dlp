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
    InputFile,
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
    MessageHandler,
    filters,
)

import config
import database as db
# import fileserver  # файловый сервер: раскомментировать при включении
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


# ── Основные команды ─────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)

    if db.is_admin(user.id) or db.is_authorized(user.id):
        text = (
            f"👋 Привет, <b>{_esc(user.first_name)}</b>!\n\n"
            "Я помогу тебе скачать видео или аудио с популярных сайтов.\n"
            "Просто отправь мне ссылку на видео!\n\n"
            + SUPPORTED_SITES_TEXT +
            "\n\n📋 <b>Команды:</b>\n"
            "/help — справка\n"
            "/history — история загрузок\n"
            "/status — статус бота"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📖 Справка", callback_data="menu:help"),
                InlineKeyboardButton("📜 История", callback_data="menu:history"),
                InlineKeyboardButton("📊 Статус", callback_data="menu:status"),
            ]
        ])
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=keyboard,
        )
    else:
        await _send_access_request(update, ctx)


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
        title = (row["title"] or row["url"])[:50]
        lines.append(f"{i}. {status_icon} {title}")
        if row["quality"]:
            lines.append(f"   └ {row['quality']}, {_human_size(row['file_size'])}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@require_auth
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    stats = db.get_global_stats()
    disk = shutil.disk_usage(str(config.DOWNLOAD_DIR))
    text = (
        "📊 <b>Статус бота</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📥 Всего загрузок: {stats['total_downloads']}\n"
        f"💾 Объём отправленного: {_human_size(stats['total_size_bytes'])}\n"
        f"⏳ Ожидают одобрения: {stats['pending_requests']}\n\n"
        f"🖥 Диск: {_human_size(disk.free)} свободно / {_human_size(disk.total)} всего"
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

def _strip_playlist_param(url: str) -> str:
    """Убирает параметры list= и index= из YouTube URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop("list", None)
    params.pop("index", None)
    params.pop("start_radio", None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
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
    url = update.message.text.strip()

    if not is_supported_url(url):
        await update.message.reply_text(
            "❓ Ссылка не распознана как поддерживаемая.\n\n"
            "Отправьте прямую ссылку на страницу видео.\n"
            + SUPPORTED_SITES_TEXT,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    # Если YouTube URL с и video, и playlist — предлагаем выбор
    if _is_youtube_mixed_url(url):
        clean_url = _strip_playlist_param(url)
        ctx.user_data[KEY_PENDING_URL] = clean_url
        ctx.user_data[KEY_ORIG_URL] = url
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📹 Скачать это видео", callback_data="resolve:video")],
            [InlineKeyboardButton("📋 Скачать плейлист целиком", callback_data="resolve:playlist")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
        ])
        await update.message.reply_text(
            "🔗 Ссылка содержит и видео, и плейлист.\n"
            "Что вы хотите скачать?",
            reply_markup=keyboard,
        )
        return

    msg = await update.message.reply_text("🔍 Получаю информацию о видео…")
    await _fetch_and_show_menu(url, msg, ctx)


async def _fetch_and_show_menu(url: str, msg: Message, ctx: ContextTypes.DEFAULT_TYPE):
    """Получает информацию о видео и показывает меню выбора качества."""
    try:
        info: VideoInfo = await get_video_info(url)
    except Exception as e:
        logger.error("get_video_info error: %s", e)
        await msg.edit_text(
            f"❌ Не удалось получить информацию о видео:\n<code>{_esc(str(e)[:300])}</code>",
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
            try:
                db.save_session(sent.chat_id, sent.message_id, url, _serialize_video_info(info))
            except Exception as e:
                logger.warning("save_session failed: %s", e)


# ── Меню видео ───────────────────────────────────────────────────────────────────

def _build_quality_menu(info: VideoInfo) -> tuple[str, InlineKeyboardMarkup]:
    """Строит текст и клавиатуру меню выбора качества. Используется при показе и возврате."""
    video_fmts = get_best_video_formats(info.formats)
    likes_str = f"  👍 {_fmt_num(info.like_count)}" if info.like_count else ""
    caption = (
        f"🎬 <b>{_esc(info.title)}</b>\n"
        f"👤 {_esc(info.uploader or '—')}\n"
        f"⏱ {info.duration_str}  👁 {info.views_str}{likes_str}\n"
        f"🌐 {_esc(info.extractor or '—')}\n\n"
        "Выберите качество для загрузки:"
    )
    buttons = []
    for f in video_fmts:
        size_hint = f" [{f.size_str}]" if f.filesize or f.tbr else ""
        fps_hint = f" {f.fps}fps" if f.fps and f.fps > 30 else ""
        label = f"🎥 {f.resolution}{fps_hint} {f.ext.upper()}{size_hint}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dl:v:{f.format_id}")])
    buttons.append([InlineKeyboardButton("⚡ Лучшее качество (авто)", callback_data="dl:v:best")])
    if config.ALLOW_AUDIO:
        buttons.append([InlineKeyboardButton("🎵 Только аудио (MP3 192kbps)", callback_data="dl:a:best")])
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
    try:
        if info.thumbnail:
            await msg.delete()
            sent = await ctx.bot.send_photo(
                msg.chat_id,
                photo=info.thumbnail,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            return sent
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
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Первые 5 видео (лучшее качество)", callback_data="pl:5:best")],
        [InlineKeyboardButton("📥 Первые 10 видео (лучшее качество)", callback_data="pl:10:best")],
        [InlineKeyboardButton("🎵 Только аудио — первые 5", callback_data="pl:5:audio")],
        [InlineKeyboardButton("🎵 Только аудио — первые 10", callback_data="pl:10:audio")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ])
    await msg.edit_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


# ── Callback-обработчик ──────────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()

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
            # Загрузка активна — устанавливаем флаг, меню вернётся автоматически
            cancel_flag[0] = True
            await query.answer("Отменяем загрузку…", show_alert=False)
            return
        # Пользователь явно закрывает меню — удаляем сессию из БД
        try:
            db.delete_session(query.message.chat_id, query.message.message_id)
        except Exception:
            pass
        ctx.user_data.clear()
        await query.edit_message_text("🛑 Отменено.")
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

    if data.startswith("dl:"):
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
            text += "\n/pending, /users, /ban, /stats"
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
        else:
            lines = ["📜 <b>Последние загрузки:</b>\n"]
            for i, row in enumerate(rows, 1):
                icon = {"done": "✅", "error": "❌", "pending": "⏳"}.get(row["status"], "•")
                title = (row["title"] or row["url"])[:50]
                lines.append(f"{i}. {icon} {title}")
            text = "\n".join(lines)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="menu:back"),
            ]]),
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
        user_obj = query.from_user
        text = (
            f"👋 Привет, <b>{_esc(user_obj.first_name)}</b>!\n\n"
            "Я помогу тебе скачать видео или аудио с популярных сайтов.\n"
            "Просто отправь мне ссылку на видео!\n\n"
            + SUPPORTED_SITES_TEXT +
            "\n\n📋 <b>Команды:</b>\n"
            "/help — справка\n"
            "/history — история загрузок\n"
            "/status — статус бота"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📖 Справка", callback_data="menu:help"),
                InlineKeyboardButton("📜 История", callback_data="menu:history"),
                InlineKeyboardButton("📊 Статус", callback_data="menu:status"),
            ]
        ])
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
                uname = f"@{r['username']}" if r['username'] else r['full_name']
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


async def _handle_download_callback(query, ctx, data: str):
    # data: dl:<type>:<format_id>   type: v=video, a=audio, s=subtitle
    parts = data.split(":", 2)
    dl_type = parts[1]
    format_id = parts[2]

    # Проверяем лимит одновременных загрузок
    sem: asyncio.Semaphore = ctx.bot_data.get("_download_sem")
    if sem is not None and sem._value <= 0:
        await query.answer(
            f"⚠️ Достигнут лимит одновременных загрузок ({config.MAX_CONCURRENT_DOWNLOADS}). "
            "Подождите завершения текущих загрузок.",
            show_alert=True,
        )
        return

    info: VideoInfo = ctx.user_data.get(KEY_VIDEO_INFO)
    url = ctx.user_data.get(KEY_PENDING_URL)
    if not info or not url:
        # Пробуем восстановить сессию из БД (пережила перезапуск бота)
        session = db.get_session(query.message.chat_id, query.message.message_id)
        if session:
            try:
                info = _deserialize_video_info(session["video_info_json"])
                url = session["url"]
                ctx.user_data[KEY_VIDEO_INFO] = info
                ctx.user_data[KEY_PENDING_URL] = url
            except Exception as e:
                logger.warning("restore_session failed: %s", e)
        if not info or not url:
            # query.answer работает и для фото-сообщений (edit_message_text — нет)
            await query.answer("❌ Сессия истекла. Отправьте ссылку заново.", show_alert=True)
            return

    # Сохраняем до возможного удаления сообщения (при фото-меню)
    _session_chat_id = query.message.chat_id
    _session_msg_id  = query.message.message_id

    user = query.from_user
    dl_id = db.add_download(user.id, url)
    ctx.user_data[KEY_DOWNLOAD_ID] = dl_id

    audio_only = dl_type == "a"
    subtitle_lang = format_id if dl_type == "s" else None
    if dl_type == "s":
        format_id = "best"

    if dl_type == "a":
        quality_label = "Аудио MP3"
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

    # Проверяем известный размер файла ДО начала загрузки
    if fmt_obj and fmt_obj.filesize and fmt_obj.filesize > config.MAX_FILE_SIZE_BYTES:
        await query.answer(
            f"❌ Файл слишком большой: ~{_human_size(fmt_obj.filesize)}\n"
            f"Лимит: {config.MAX_FILE_SIZE_MB} МБ ({_human_size(config.MAX_FILE_SIZE_BYTES)})",
            show_alert=True,
        )
        db.update_download(dl_id, status="error", error="pre-check: file too large")
        return

    db.update_download(dl_id, title=info.title, format_id=format_id, quality=quality_label, status="downloading")

    cancel_flag = [False]
    ctx.user_data["cancel_flag"] = cancel_flag
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
        if cancel_flag[0] or not tracker.total:
            return
        pct = tracker.downloaded / tracker.total * 100
        speed_str = f"{tracker.speed / 1_048_576:.1f} МБ/с" if tracker.speed else "—"
        if tracker.eta:
            m, s = divmod(int(tracker.eta), 60)
            eta_str = f"{m}м {s:02d}с" if m else f"{s}с"
        else:
            eta_str = "—"
        try:
            await status_msg.edit_text(
                f"⬇️ Загружаю: <b>{_esc(info.title)}</b>\n"
                f"Качество: {quality_label}\n\n"
                f"⏳ {pct:.1f}% • {speed_str} • ETA: {eta_str}",
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
    async with (sem or asyncio.Semaphore(1)):
        try:
            result: DownloadResult = await download_video(
                url=url,
                format_id=format_id,
                output_dir=tmp_dir,
                audio_only=audio_only,
                subtitle_lang=subtitle_lang,
                progress_callback=_on_progress,
                cancel_flag=cancel_flag,
            )

            ctx.user_data.pop("cancel_flag", None)

            if not result.success:
                _caption, _keyboard = _build_quality_menu(info)
                if result.error == "CANCELLED":
                    # Отмена — возвращаем меню выбора качества
                    try:
                        await status_msg.edit_text(_caption, parse_mode=ParseMode.HTML, reply_markup=_keyboard)
                    except TelegramError:
                        pass
                    return
                db.update_download(dl_id, status="error", error=result.error)
                try:
                    await status_msg.edit_text(
                        f"❌ Ошибка: <code>{_esc(result.error[:300])}</code>\n\n{_caption}",
                        parse_mode=ParseMode.HTML,
                        reply_markup=_keyboard,
                    )
                except TelegramError:
                    pass
                return

            db.update_download(dl_id, status="sending", file_size=result.file_size)
            await status_msg.edit_text(
                f"📤 Отправляю <b>{_esc(result.title or info.title)}</b> "
                f"({_human_size(result.file_size)})…",
                parse_mode=ParseMode.HTML,
            )
            await ctx.bot.send_chat_action(query.message.chat_id, ChatAction.UPLOAD_DOCUMENT)

            await _deliver_file(query.message.chat_id, result, ctx.bot)
            db.update_download(dl_id, status="done", file_size=result.file_size)

            # Возвращаем меню выбора качества — пользователь может скачать другой формат
            _caption, _keyboard = _build_quality_menu(info)
            try:
                await status_msg.edit_text(
                    f"✅ <b>{_esc(result.title or info.title)}</b>  {_human_size(result.file_size)}\n\n"
                    + _caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=_keyboard,
                )
            except TelegramError:
                pass

            # Обновляем сессию (сбрасываем 2-часовой таймер очистки)
            try:
                db.save_session(status_msg.chat_id, status_msg.message_id, url, _serialize_video_info(info))
            except Exception:
                pass

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
            # KEY_VIDEO_INFO и KEY_PENDING_URL не очищаем — пользователь может
            # скачать другой формат без повторной отправки ссылки.
            # Сессия удаляется только при явной отмене (❌ Отмена).


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
        for r in results:
            if r.success and r.file_path and r.file_path.exists():
                if r.file_size <= config.MAX_FILE_SIZE_BYTES:
                    await _deliver_file(query.message.chat_id, r, ctx.bot)
                    sent += 1
                    await asyncio.sleep(1)
                else:
                    skipped += 1

        db.update_download(dl_id, title=info.title, status="done")
        summary = f"✅ Плейлист загружен. Отправлено: {sent}/{len(results)}"
        if skipped:
            summary += f" (пропущено {skipped} — превышен лимит размера)"
        await ctx.bot.send_message(query.message.chat_id, summary)

    except Exception as e:
        logger.error("Playlist error: %s", e)
        db.update_download(dl_id, status="error", error=str(e))
        await ctx.bot.send_message(
            query.message.chat_id,
            f"❌ Ошибка при загрузке плейлиста:\n<code>{_esc(str(e)[:300])}</code>",
            parse_mode=ParseMode.HTML,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _deliver_file(chat_id: int, result: DownloadResult, bot: Bot, keep_file: bool = False):
    """
    Отправляет файл напрямую через Telegram Bot API (локальный сервер снимает лимит 2 ГБ).

    # ── Режим файлового HTTP-сервера (закомментировано) ─────────────────────────────
    # При включении: раскомментировать import fileserver, _post_init и .post_init() в main(),
    # задать PUBLIC_BASE_URL в .env — бот отправит ссылку вместо файла.
    #
    # if config.PUBLIC_BASE_URL:
    #     token = fileserver.register_file(fp, ttl_seconds=config.FILE_TTL_SECONDS)
    #     url = f"{config.PUBLIC_BASE_URL}/dl/{token}"
    #     ttl_h = config.FILE_TTL_SECONDS // 3600
    #     ttl_label = f"{ttl_h} ч" if ttl_h < 24 else f"{ttl_h // 24} д"
    #     await bot.send_message(
    #         chat_id,
    #         f"📥 <b>Файл готов!</b>\n\n"
    #         f"🔗 <a href='{url}'>{_esc(fp.name)}</a>\n"
    #         f"📦 Размер: {_human_size(result.file_size)}\n"
    #         f"⏳ Ссылка действительна: {ttl_label} (удаляется после скачивания)",
    #         parse_mode=ParseMode.HTML,
    #         disable_web_page_preview=True,
    #     )
    #     return
    # ─────────────────────────────────────────────────────────────────────────────────
    """
    fp = result.file_path
    caption = f"📁 {fp.stem[:200]}  ({_human_size(result.file_size)})"

    if config.LOCAL_API_SERVER:
        # local_mode=True: передаём абсолютный путь к файлу.
        # Локальный Bot API сервер читает файл напрямую с диска через
        # общий том /downloads — не нужен HTTP-upload от бота к серверу.
        # Это устраняет узкое место при отправке больших файлов.
        fp_path = fp.resolve()
        if fp.suffix in (".mp3", ".ogg", ".m4a", ".flac", ".wav"):
            await bot.send_audio(chat_id, audio=fp_path, caption=caption)
        else:
            await bot.send_document(chat_id, document=fp_path, caption=caption)
    else:
        with fp.open("rb") as fh:
            if fp.suffix in (".mp3", ".ogg", ".m4a", ".flac", ".wav"):
                await bot.send_audio(chat_id, audio=InputFile(fh, filename=fp.name), caption=caption)
            else:
                await bot.send_document(chat_id, document=InputFile(fh, filename=fp.name), caption=caption)

    if not keep_file:
        fp.unlink(missing_ok=True)


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
        uname = f"@{r['username']}" if r['username'] else r['full_name']
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


# ── PTB lifecycle hooks (файловый сервер — закомментировано) ─────────────────────
#
# async def _post_init(application: Application) -> None:
#     """Запускает файловый HTTP-сервер вместе с ботом."""
#     if config.PUBLIC_BASE_URL:
#         await fileserver.start(port=config.HTTP_PORT)
#         logger.info(
#             "Файловый сервер: порт %d, публичный URL: %s",
#             config.HTTP_PORT, config.PUBLIC_BASE_URL,
#         )
#     else:
#         logger.info("PUBLIC_BASE_URL не задан — файлы отправляются напрямую в Telegram")


# ── Периодическая очистка (asyncio, без APScheduler) ─────────────────────────────

async def _cleanup_loop() -> None:
    """Фоновый цикл: очистка каждый час. Запускается через post_init."""
    while True:
        await asyncio.sleep(3600)
        try:
            await _cleanup_job()
        except Exception as e:
            logger.error("Ошибка очистки: %s", e)


async def _post_init(application) -> None:
    application.bot_data["_download_sem"] = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
    task = asyncio.create_task(_cleanup_loop())
    application.bot_data["_cleanup_task"] = task
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


async def _cleanup_job() -> None:
    """Каждый час: удаляет файлы и данные старше 2 часов."""
    removed_dirs = 0
    cutoff_ts = datetime.now().timestamp() - 7200  # 2 часа

    if config.DOWNLOAD_DIR.exists():
        for item in config.DOWNLOAD_DIR.iterdir():
            try:
                if item.stat().st_mtime < cutoff_ts:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    removed_dirs += 1
            except Exception:
                pass

    old_sessions = db.cleanup_old_sessions(max_age_hours=2)
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

    app.add_error_handler(error_handler)

    logger.info("Бот запускается… Администраторы: %s", config.ADMIN_IDS)
    app.run_polling(drop_pending_updates=True, bootstrap_retries=5)


if __name__ == "__main__":
    main()
