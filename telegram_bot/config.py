import os
from pathlib import Path

# Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

# Download settings
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "/downloads"))
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "10240"))  # 10 ГБ
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Локальный Telegram Bot API сервер (снимает лимит 50 МБ → до 2 ГБ)
# При использовании docker-compose значение: http://telegram-bot-api:8081
LOCAL_API_SERVER = os.environ.get("LOCAL_API_SERVER", "http://telegram-bot-api:8081")

# Concurrency
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "3"))

# Database
DB_PATH = Path(os.environ.get("DB_PATH", "/data/bot.db"))

# Limits
MAX_HISTORY_PER_USER = int(os.environ.get("MAX_HISTORY_PER_USER", "50"))
DOWNLOAD_TIMEOUT = int(os.environ.get("DOWNLOAD_TIMEOUT", "3600"))  # seconds (1 час для больших файлов)

# Файловый HTTP-сервер (вместо отправки файла в Telegram — даёт ссылку на скачивание)
# PUBLIC_BASE_URL — публичный адрес, который видят пользователи (без trailing slash)
#   Пример: https://myserver.com  или  http://1.2.3.4:8080
#   Если пусто — бот отправляет файл напрямую в Telegram (старое поведение)
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8080"))
# Сколько секунд ссылка остаётся активной (по умолчанию 24 часа)
FILE_TTL_SECONDS = int(os.environ.get("FILE_TTL_HOURS", "24")) * 3600

# Feature flags
ALLOW_PLAYLISTS = os.environ.get("ALLOW_PLAYLISTS", "true").lower() == "true"
ALLOW_AUDIO = os.environ.get("ALLOW_AUDIO", "true").lower() == "true"
ALLOW_SUBTITLES = os.environ.get("ALLOW_SUBTITLES", "true").lower() == "true"
# aria2c: параллельные соединения ускоряют загрузку больших файлов по HTTP
# Требует aria2 в системе (уже установлен в Dockerfile)
USE_ARIA2C = os.environ.get("USE_ARIA2C", "true").lower() == "true"
# SponsorBlock: убирать рекламные вставки из YouTube-видео
USE_SPONSORBLOCK = os.environ.get("USE_SPONSORBLOCK", "false").lower() == "true"

# Proxy (optional)
PROXY_URL = os.environ.get("PROXY_URL", "")

# Cookie file path for age-restricted content
COOKIES_FILE = os.environ.get("COOKIES_FILE", "")

# Registration mode: "open" (anyone can register) or "closed" (admin approves only)
REGISTRATION_MODE = os.environ.get("REGISTRATION_MODE", "closed")
