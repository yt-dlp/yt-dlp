# YT-DLP Telegram Bot

A fully-featured, Docker-ready Telegram bot that wraps **yt-dlp** to let
authorised users download videos and audio from YouTube and thousands of
other sites — all via a clean inline-button interface.

---

## Features

| Feature | Description |
|---------|-------------|
| 🔐 Access control | Only approved users can use the bot |
| 🎬 Video download | Choose from all available resolutions |
| 🎵 Audio extraction | MP3 download with one tap |
| 📋 Playlists | Download first N items of a playlist |
| 📄 Subtitles | Download video with embedded subtitles |
| 📜 History | Per-user download history |
| 👑 Admin panel | Approve/ban users, view stats |
| 🐳 Docker | Single `docker compose up -d` deploy |
| 💾 SQLite | Zero-config persistent storage |
| 🔔 Admin notifications | Instant approval-request alerts |

---

## Quick Start

### 1. Create a Telegram bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the **API token**

### 2. Find your Telegram user ID

Send any message to [@userinfobot](https://t.me/userinfobot) — it replies
with your numeric ID (e.g. `123456789`).

### 3. Configure

```bash
cp .env.example .env
# Edit .env — at minimum set BOT_TOKEN and ADMIN_IDS
nano .env
```

### 4. Create data directories

```bash
mkdir -p data/downloads data/db
```

### 5. Build & run

```bash
docker compose up -d --build
```

Check logs:
```bash
docker compose logs -f ytdlp-bot
```

---

## Usage

### User flow

1. Send `/start` — if you're not approved yet, the admin gets a notification
2. Once approved, send any video URL
3. The bot shows video info + quality buttons
4. Tap a quality → bot downloads and sends the file

### Commands (all users)

| Command | Description |
|---------|-------------|
| `/start` | Welcome & registration |
| `/help` | Command reference |
| `/history` | Last 10 downloads |
| `/status` | Bot & disk stats |
| `/cancel` | Cancel current operation |

### Commands (admin only)

| Command | Description |
|---------|-------------|
| `/pending` | List pending access requests |
| `/users` | List all approved users |
| `/approve <id>` | Approve a user |
| `/deny <id>` | Remove/deny a user |
| `/ban <id>` | Ban a user |
| `/unban <id>` | Unban a user |
| `/addadmin <id>` | Promote user to admin |
| `/stats` | Global download statistics |

---

## Configuration reference

All settings are in `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | — | **Required.** Telegram bot token |
| `ADMIN_IDS` | — | **Required.** Comma-separated admin user IDs |
| `REGISTRATION_MODE` | `closed` | `closed` = admin approves; `open` = anyone |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size (Telegram limit: 50 MB) |
| `DOWNLOAD_TIMEOUT` | `600` | Per-download timeout (seconds) |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Parallel download limit |
| `ALLOW_PLAYLISTS` | `true` | Enable playlist downloads |
| `ALLOW_AUDIO` | `true` | Enable audio-only (MP3) |
| `ALLOW_SUBTITLES` | `true` | Enable subtitle download |
| `PROXY_URL` | — | HTTP/SOCKS5 proxy URL |
| `COOKIES_FILE` | — | Path to Netscape cookies file |

---

## Age-restricted / login-required videos

Export your browser cookies with a browser extension such as
[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
and place the file at `./cookies.txt`, then uncomment the volume line in
`docker-compose.yml` and set `COOKIES_FILE=/cookies.txt` in `.env`.

---

## Updating

```bash
git pull
docker compose up -d --build
```

---

## File size limits

Telegram bots can send files up to **50 MB**. For larger downloads, the bot
will inform you that the file is too big. You can work around this by:

- Choosing a lower quality
- Using audio-only mode
- Increasing `MAX_FILE_SIZE_MB` — note this won't bypass Telegram's hard cap

---

## Security notes

- The `.env` file contains your bot token — **never commit it to git**
  (`.gitignore` already excludes `.env`)
- The bot runs as a non-root user inside Docker
- Only approved users can trigger downloads

---

## Architecture

```
telegram_bot/
├── bot.py          — Telegram handlers, inline menus, admin commands
├── downloader.py   — yt-dlp wrapper (async, format parsing, progress)
├── database.py     — SQLite: users, download history, stats
├── config.py       — Settings from environment variables
└── requirements.txt

Dockerfile          — Python 3.12 + ffmpeg + yt-dlp from source
docker-compose.yml  — Service definition with volumes and resource limits
.env.example        — Configuration template
```
