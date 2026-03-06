#!/usr/bin/env python3
"""
YT-DLP Telegram Bot
────────────────────────────────────────────────────────────
A full-featured, access-controlled Telegram bot that wraps
yt-dlp to let authorised users download videos and audio
from YouTube and thousands of other sites.
"""

import asyncio
import logging
import os
import re
import shutil
import tempfile
import traceback
from functools import wraps
from pathlib import Path
from typing import Optional

from telegram import (
    Bot,
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
from downloader import (
    DownloadResult,
    VideoInfo,
    download_video,
    get_audio_formats,
    get_best_video_formats,
    get_video_info,
    is_supported_url,
)

# ── Logging ─────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Session state keys ──────────────────────────────────────────────────────────
# stored in context.user_data

KEY_VIDEO_INFO = "video_info"       # VideoInfo object
KEY_DOWNLOAD_ID = "download_id"     # DB row id
KEY_PENDING_URL = "pending_url"


# ── Decorators ──────────────────────────────────────────────────────────────────

def require_auth(func):
    """Reject users who are not approved."""
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
                    "⏳ Your access request is pending admin approval.\n"
                    "You will be notified when approved."
                )
            elif row and row["is_banned"]:
                await update.effective_message.reply_text("🚫 You are banned from using this bot.")
            else:
                await _send_access_request(update, ctx)
            return
        return await func(update, ctx)
    return wrapper


def require_admin(func):
    """Reject non-admins."""
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not db.is_admin(user.id):
            await update.effective_message.reply_text("🚫 Admin access required.")
            return
        return await func(update, ctx)
    return wrapper


# ── Access-request flow ─────────────────────────────────────────────────────────

async def _send_access_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)

    if config.REGISTRATION_MODE == "open":
        db.approve_user(user.id, 0)
        await update.effective_message.reply_text(
            "✅ Registration is open! You now have access.\n"
            "Send /start to begin."
        )
        return

    await update.effective_message.reply_text(
        "👋 Welcome! This is a private bot.\n\n"
        "Your access request has been sent to the admin.\n"
        "Please wait for approval."
    )

    # Notify admins
    uname = f"@{user.username}" if user.username else user.full_name
    msg = (
        f"🔔 <b>New access request</b>\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🔗 Username: {uname}\n"
        f"🆔 ID: <code>{user.id}</code>"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{user.id}"),
        InlineKeyboardButton("🚫 Deny", callback_data=f"deny:{user.id}"),
    ]])
    for admin_id in config.ADMIN_IDS:
        try:
            await ctx.bot.send_message(admin_id, msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except TelegramError:
            pass


# ── Core handlers ────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.full_name)

    if db.is_admin(user.id) or db.is_authorized(user.id):
        await update.message.reply_text(
            f"👋 Hello, <b>{user.first_name}</b>!\n\n"
            "Send me a video URL and I'll help you download it.\n\n"
            "Supported: YouTube, Instagram, TikTok, Twitter/X, "
            "Twitch, SoundCloud, and <a href='https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md'>1000+ more sites</a>.\n\n"
            "📋 Commands:\n"
            "/help — full help\n"
            "/history — your download history\n"
            "/status — bot status",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    else:
        await _send_access_request(update, ctx)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    is_adm = db.is_admin(update.effective_user.id)
    text = (
        "📖 <b>Bot Help</b>\n\n"
        "<b>Basic usage:</b>\n"
        "1. Send a video URL\n"
        "2. Choose quality or audio\n"
        "3. Wait for the download\n\n"
        "<b>Commands:</b>\n"
        "/start — welcome screen\n"
        "/help — this message\n"
        "/history — last 10 downloads\n"
        "/status — bot &amp; server stats\n"
        "/cancel — cancel current operation\n"
    )
    if is_adm:
        text += (
            "\n<b>Admin commands:</b>\n"
            "/pending — pending access requests\n"
            "/users — list approved users\n"
            "/approve &lt;id&gt; — approve user\n"
            "/deny &lt;id&gt; — deny/remove user\n"
            "/ban &lt;id&gt; — ban user\n"
            "/unban &lt;id&gt; — unban user\n"
            "/addadmin &lt;id&gt; — promote to admin\n"
            "/stats — global download stats\n"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@require_auth
async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = db.get_user_history(update.effective_user.id, limit=10)
    if not rows:
        await update.message.reply_text("📭 No download history yet.")
        return

    lines = ["📜 <b>Your last downloads:</b>\n"]
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
        "📊 <b>Bot Status</b>\n\n"
        f"👥 Users: {stats['total_users']}\n"
        f"📥 Total downloads: {stats['total_downloads']}\n"
        f"💾 Total downloaded: {_human_size(stats['total_size_bytes'])}\n"
        f"⏳ Pending requests: {stats['pending_requests']}\n\n"
        f"🖥 Disk free: {_human_size(disk.free)} / {_human_size(disk.total)}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@require_auth
async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("🛑 Cancelled. Send a new URL whenever you're ready.")


# ── URL handler ──────────────────────────────────────────────────────────────────

@require_auth
async def handle_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user = update.effective_user

    if not is_supported_url(url):
        await update.message.reply_text(
            "❓ That doesn't look like a supported URL.\n"
            "Send a direct link to a video page."
        )
        return

    msg = await update.message.reply_text("🔍 Fetching video info…")

    try:
        info: VideoInfo = await get_video_info(url)
    except Exception as e:
        logger.error("get_video_info error: %s", e)
        await msg.edit_text(f"❌ Could not fetch video info:\n<code>{str(e)[:300]}</code>", parse_mode=ParseMode.HTML)
        return

    ctx.user_data[KEY_VIDEO_INFO] = info
    ctx.user_data[KEY_PENDING_URL] = url

    if info.is_playlist:
        await _show_playlist_menu(msg, info, ctx)
    else:
        await _show_video_menu(msg, info, ctx)


async def _show_video_menu(msg: Message, info: VideoInfo, ctx: ContextTypes.DEFAULT_TYPE):
    video_fmts = get_best_video_formats(info.formats)
    audio_fmts = get_audio_formats(info.formats)

    caption = (
        f"🎬 <b>{_esc(info.title)}</b>\n"
        f"👤 {_esc(info.uploader)}\n"
        f"⏱ {info.duration_str}  👁 {info.views_str} views\n\n"
        "Choose quality to download:"
    )

    buttons = []

    # Video quality buttons
    for f in video_fmts:
        size_hint = f" [{f.size_str}]" if f.filesize else ""
        label = f"🎥 {f.resolution}"
        if f.fps and f.fps > 30:
            label += f" {f.fps}fps"
        label += f" {f.ext.upper()}{size_hint}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dl:v:{f.format_id}")])

    # Best-quality shortcut
    buttons.append([InlineKeyboardButton("⚡ Best quality (auto)", callback_data="dl:v:best")])

    # Audio button
    if config.ALLOW_AUDIO:
        buttons.append([InlineKeyboardButton("🎵 Audio only (MP3)", callback_data="dl:a:best")])

    # Subtitles button
    if config.ALLOW_SUBTITLES:
        buttons.append([InlineKeyboardButton("📄 Download with subtitles (EN)", callback_data="dl:s:en")])

    # Info button
    buttons.append([InlineKeyboardButton("ℹ️ More info", callback_data="info")])

    keyboard = InlineKeyboardMarkup(buttons)

    try:
        if info.thumbnail:
            await msg.delete()
            await ctx.bot.send_photo(
                msg.chat_id,
                photo=info.thumbnail,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            return
    except TelegramError:
        pass

    await msg.edit_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def _show_playlist_menu(msg: Message, info: VideoInfo, ctx: ContextTypes.DEFAULT_TYPE):
    if not config.ALLOW_PLAYLISTS:
        await msg.edit_text("⚠️ Playlist downloads are disabled.")
        return

    caption = (
        f"📋 <b>Playlist: {_esc(info.title)}</b>\n"
        f"🎬 {info.playlist_count} videos\n\n"
        "Playlists are large. Choose an action:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Download first 5 videos (best)", callback_data="pl:5:best")],
        [InlineKeyboardButton("📥 Download first 10 videos (best)", callback_data="pl:10:best")],
        [InlineKeyboardButton("🎵 Audio only – first 5", callback_data="pl:5:audio")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ])
    await msg.edit_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


# ── Callback query handler ──────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    data = query.data

    # Admin approval buttons (available without full auth)
    if data.startswith("approve:") or data.startswith("deny:"):
        await _handle_admin_approval(query, ctx, data)
        return

    if data == "cancel":
        ctx.user_data.clear()
        await query.edit_message_text("🛑 Cancelled.")
        return

    if data == "info":
        info: VideoInfo = ctx.user_data.get(KEY_VIDEO_INFO)
        if not info:
            await query.edit_message_text("❌ Session expired. Send the URL again.")
            return
        await _show_info(query, info)
        return

    # Auth check for download actions
    if not db.is_authorized(user.id) and not db.is_admin(user.id):
        await query.answer("🚫 Access denied.", show_alert=True)
        return

    if data.startswith("dl:"):
        await _handle_download_callback(query, ctx, data)
    elif data.startswith("pl:"):
        await _handle_playlist_callback(query, ctx, data)


async def _show_info(query, info: VideoInfo):
    text = (
        f"ℹ️ <b>{_esc(info.title)}</b>\n\n"
        f"👤 Uploader: {_esc(info.uploader)}\n"
        f"⏱ Duration: {info.duration_str}\n"
        f"👁 Views: {info.views_str}\n"
        f"🌐 Site: {info.extractor}\n"
    )
    if info.description:
        text += f"\n📝 {_esc(info.description[:300])}…"
    await query.edit_message_caption(text, parse_mode=ParseMode.HTML)


async def _handle_admin_approval(query, ctx, data: str):
    if not db.is_admin(query.from_user.id):
        await query.answer("Not authorised.", show_alert=True)
        return

    action, uid_str = data.split(":", 1)
    target_id = int(uid_str)

    if action == "approve":
        ok = db.approve_user(target_id, query.from_user.id)
        if ok:
            await query.edit_message_text(f"✅ User {target_id} approved.")
            try:
                await ctx.bot.send_message(
                    target_id,
                    "✅ Your access request has been approved! Send /start to begin."
                )
            except TelegramError:
                pass
        else:
            await query.answer("User not found.", show_alert=True)
    else:
        db.ban_user(target_id)
        await query.edit_message_text(f"🚫 User {target_id} denied/banned.")
        try:
            await ctx.bot.send_message(target_id, "❌ Your access request was denied.")
        except TelegramError:
            pass


async def _handle_download_callback(query, ctx, data: str):
    # data format: dl:<type>:<format_id>
    # type: v=video, a=audio, s=subtitle
    parts = data.split(":", 2)
    dl_type = parts[1]
    format_id = parts[2]

    info: VideoInfo = ctx.user_data.get(KEY_VIDEO_INFO)
    url = ctx.user_data.get(KEY_PENDING_URL)
    if not info or not url:
        await query.edit_message_text("❌ Session expired. Send the URL again.")
        return

    user = query.from_user
    dl_id = db.add_download(user.id, url)
    ctx.user_data[KEY_DOWNLOAD_ID] = dl_id

    audio_only = dl_type == "a"
    subtitle_lang = format_id if dl_type == "s" else None
    if dl_type == "s":
        format_id = "best"

    quality_label = {
        "a": "Audio MP3",
        "s": f"Subtitles ({subtitle_lang})",
    }.get(dl_type, format_id)

    db.update_download(dl_id, title=info.title, format_id=format_id, quality=quality_label, status="downloading")

    status_msg = await query.edit_message_text(
        f"⬇️ Downloading: <b>{_esc(info.title)}</b>\n"
        f"Quality: {quality_label}\n\n"
        "⏳ Please wait…",
        parse_mode=ParseMode.HTML,
    )

    await ctx.bot.send_chat_action(query.message.chat_id, ChatAction.UPLOAD_DOCUMENT)

    # Per-user temp directory
    tmp_dir = config.DOWNLOAD_DIR / f"user_{user.id}" / f"dl_{dl_id}"
    try:
        result: DownloadResult = await download_video(
            url=url,
            format_id=format_id,
            output_dir=tmp_dir,
            audio_only=audio_only,
            subtitle_lang=subtitle_lang,
        )

        if not result.success:
            db.update_download(dl_id, status="error", error=result.error)
            await status_msg.edit_text(
                f"❌ Download failed:\n<code>{_esc(result.error)}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        db.update_download(dl_id, status="sending", file_size=result.file_size)
        await status_msg.edit_text(
            f"📤 Uploading <b>{_esc(result.title or info.title)}</b> "
            f"({_human_size(result.file_size)})…",
            parse_mode=ParseMode.HTML,
        )
        await ctx.bot.send_chat_action(query.message.chat_id, ChatAction.UPLOAD_DOCUMENT)

        await _send_file(query.message.chat_id, result, ctx.bot)
        db.update_download(dl_id, status="done", file_size=result.file_size)

        await status_msg.edit_text(
            f"✅ <b>{_esc(result.title or info.title)}</b>\n"
            f"Size: {_human_size(result.file_size)}\n\n"
            "Send another URL anytime!",
            parse_mode=ParseMode.HTML,
        )

    except Exception as e:
        logger.error("Download error: %s\n%s", e, traceback.format_exc())
        db.update_download(dl_id, status="error", error=str(e))
        await status_msg.edit_text(
            f"❌ Unexpected error:\n<code>{_esc(str(e)[:300])}</code>",
            parse_mode=ParseMode.HTML,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        ctx.user_data.pop(KEY_VIDEO_INFO, None)
        ctx.user_data.pop(KEY_PENDING_URL, None)


async def _handle_playlist_callback(query, ctx, data: str):
    parts = data.split(":")
    max_items = int(parts[1])
    quality = parts[2]
    audio_only = quality == "audio"

    info: VideoInfo = ctx.user_data.get(KEY_VIDEO_INFO)
    url = ctx.user_data.get(KEY_PENDING_URL)
    if not info or not url:
        await query.edit_message_text("❌ Session expired.")
        return

    user = query.from_user
    dl_id = db.add_download(user.id, url)

    await query.edit_message_text(
        f"⬇️ Downloading playlist: <b>{_esc(info.title)}</b>\n"
        f"Up to {max_items} videos\n\n⏳ This may take a while…",
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
        for r in results:
            if r.success and r.file_path and r.file_path.exists():
                if r.file_size <= config.MAX_FILE_SIZE_BYTES:
                    await _send_file(query.message.chat_id, r, ctx.bot)
                    sent += 1
                    await asyncio.sleep(1)

        db.update_download(dl_id, title=info.title, status="done")
        await ctx.bot.send_message(
            query.message.chat_id,
            f"✅ Playlist done. Sent {sent}/{len(results)} files.",
        )
    except Exception as e:
        logger.error("Playlist error: %s", e)
        db.update_download(dl_id, status="error", error=str(e))
        await ctx.bot.send_message(query.message.chat_id, f"❌ Playlist error: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _send_file(chat_id: int, result: DownloadResult, bot: Bot):
    fp = result.file_path
    caption = f"📁 {fp.stem[:200]}"
    with fp.open("rb") as fh:
        if fp.suffix in (".mp3", ".ogg", ".m4a", ".flac", ".wav"):
            await bot.send_audio(chat_id, audio=InputFile(fh, filename=fp.name), caption=caption)
        elif fp.suffix in (".mp4", ".mkv", ".webm", ".mov"):
            await bot.send_video(chat_id, video=InputFile(fh, filename=fp.name), caption=caption)
        else:
            await bot.send_document(chat_id, document=InputFile(fh, filename=fp.name), caption=caption)


# ── Admin commands ───────────────────────────────────────────────────────────────

@require_admin
async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = db.pending_users()
    if not rows:
        await update.message.reply_text("✅ No pending access requests.")
        return

    for row in rows:
        uname = f"@{row['username']}" if row['username'] else "(no username)"
        text = (
            f"👤 <b>{_esc(row['full_name'])}</b> {uname}\n"
            f"🆔 <code>{row['user_id']}</code>\n"
            f"📅 Requested: {row['created_at'][:16]}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{row['user_id']}"),
            InlineKeyboardButton("🚫 Deny", callback_data=f"deny:{row['user_id']}"),
        ]])
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@require_admin
async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = db.list_users(approved=True)
    if not rows:
        await update.message.reply_text("No approved users yet.")
        return

    lines = [f"👥 <b>Approved users ({len(rows)}):</b>\n"]
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
        await update.message.reply_text(f"Usage: /{action} <user_id>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    if action == "approve":
        ok = db.approve_user(target_id, update.effective_user.id)
        msg = f"✅ User {target_id} approved." if ok else "User not found."
        if ok:
            try:
                await ctx.bot.send_message(
                    target_id,
                    "✅ Your access has been approved! Send /start to begin."
                )
            except TelegramError:
                pass
    elif action == "deny":
        db.ban_user(target_id)
        msg = f"🚫 User {target_id} removed."
    elif action == "ban":
        ok = db.ban_user(target_id)
        msg = f"🔨 User {target_id} banned." if ok else "User not found."
    elif action == "unban":
        ok = db.unban_user(target_id)
        msg = f"✅ User {target_id} unbanned." if ok else "User not found."
    elif action == "addadmin":
        ok = db.set_admin(target_id, True)
        msg = f"👑 User {target_id} promoted to admin." if ok else "User not found."
    else:
        msg = "Unknown action."

    await update.message.reply_text(msg)


@require_admin
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    stats = db.get_global_stats()
    disk = shutil.disk_usage(str(config.DOWNLOAD_DIR))
    text = (
        "📊 <b>Global Stats</b>\n\n"
        f"👥 Approved users: {stats['total_users']}\n"
        f"⏳ Pending requests: {stats['pending_requests']}\n"
        f"📥 Successful downloads: {stats['total_downloads']}\n"
        f"💾 Total data sent: {_human_size(stats['total_size_bytes'])}\n\n"
        f"🖥 Disk: {_human_size(disk.free)} free / {_human_size(disk.total)} total"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ── Error handler ────────────────────────────────────────────────────────────────

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception: %s", ctx.error, exc_info=ctx.error)


# ── Utilities ────────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _human_size(n) -> str:
    if not n:
        return "0 B"
    n = int(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ── Main ─────────────────────────────────────────────────────────────────────────

def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set!")
    if not config.ADMIN_IDS:
        raise RuntimeError("ADMIN_IDS environment variable is not set! (comma-separated Telegram user IDs)")

    db.init_db()
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-approve admins in DB
    for admin_id in config.ADMIN_IDS:
        row = db.get_user(admin_id)
        if row is None:
            db.upsert_user(admin_id, "", "Admin")
        db.approve_user(admin_id, admin_id)
        db.set_admin(admin_id, True)

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Admin commands
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("deny", cmd_deny))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # URL messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    # Inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_error_handler(error_handler)

    logger.info("Bot starting… Admin IDs: %s", config.ADMIN_IDS)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
