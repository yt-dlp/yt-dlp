from pathlib import Path

from core.models import DownloadJob
from core.runtime import bundled_ffmpeg_path


FILENAME_TEMPLATES = {
    "title": "%(title).200B [%(id)s].%(ext)s",
    "uploader-title": "%(uploader).80B - %(title).200B [%(id)s].%(ext)s",
    "date-title": "%(upload_date>%Y-%m-%d)s - %(title).200B [%(id)s].%(ext)s",
}

SPONSORBLOCK_CATEGORIES = {"sponsor"}


def _split_languages(value: str) -> list[str]:
    return [language.strip() for language in value.split(",") if language.strip()]


def _truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _int_setting(settings: dict[str, str], key: str) -> int | None:
    value = settings.get(key, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _cookies_from_browser(value: str):
    browser = value.strip()
    if not browser:
        return None
    return (browser, None, None, None)


def build_ydl_options(job: DownloadJob, app_settings: dict[str, str]) -> dict:
    template = FILENAME_TEMPLATES.get(job.filename_preset, FILENAME_TEMPLATES["title"])
    outtmpl = str(Path(job.output_dir) / template)
    postprocessors = []

    options = {
        "format": job.format_id or "bestvideo+bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": not job.playlist_mode,
        "progress_hooks": [],
    }

    if not job.audio_only and job.container:
        options["merge_output_format"] = job.container.lower()

    if job.skip_existing:
        options["overwrites"] = False
        options["continuedl"] = True

    if job.audio_only:
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": job.audio_format or "mp3",
                "preferredquality": job.audio_quality or "0",
            }
        )

    if job.write_subs:
        options["writesubtitles"] = True
        options["writeautomaticsub"] = job.write_auto_subs
        options["subtitleslangs"] = _split_languages(job.subtitle_language) or ["en"]

    if job.embed_subs:
        options["embedsubtitles"] = True

    if job.embed_metadata:
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})

    if job.embed_thumbnail:
        options["writethumbnail"] = True
        postprocessors.append({"key": "EmbedThumbnail"})

    if job.sponsorblock_mode == "skip":
        options["sponsorblock_remove"] = SPONSORBLOCK_CATEGORIES
    elif job.sponsorblock_mode == "mark":
        options["sponsorblock_mark"] = SPONSORBLOCK_CATEGORIES

    if job.split_chapters:
        options["split_chapters"] = True

    if job.playlist_items:
        options["playlist_items"] = job.playlist_items

    if job.max_downloads:
        options["max_downloads"] = job.max_downloads

    if job.live_from_start:
        options["live_from_start"] = True

    if job.wait_for_video:
        options["wait_for_video"] = job.wait_for_video

    if postprocessors:
        options["postprocessors"] = postprocessors

    ffmpeg_location = app_settings.get("ffmpeg_location") or ""
    if not ffmpeg_location and (ffmpeg := bundled_ffmpeg_path()):
        ffmpeg_location = str(ffmpeg.parent)

    settings_to_options = {
        "cookies_file": "cookiefile",
        "proxy": "proxy",
        "rate_limit": "ratelimit",
    }
    for setting_key, option_key in settings_to_options.items():
        value = app_settings.get(setting_key)
        if value:
            options[option_key] = value

    if ffmpeg_location:
        options["ffmpeg_location"] = ffmpeg_location

    for setting_key, option_key in {
        "concurrent_fragments": "concurrent_fragment_downloads",
        "retries": "retries",
        "socket_timeout": "socket_timeout",
    }.items():
        value = _int_setting(app_settings, setting_key)
        if value is not None:
            options[option_key] = value

    download_archive = app_settings.get("download_archive")
    if download_archive:
        options["download_archive"] = download_archive

    impersonate = app_settings.get("impersonate")
    if impersonate:
        options["impersonate"] = impersonate

    force_ip = app_settings.get("force_ip", "").lower()
    if force_ip == "ipv4":
        options["force_ipv4"] = True
    elif force_ip == "ipv6":
        options["force_ipv6"] = True

    cookies_from_browser = _cookies_from_browser(app_settings.get("cookies_from_browser", ""))
    if cookies_from_browser:
        options["cookiesfrombrowser"] = cookies_from_browser

    temp_path = app_settings.get("paths_temp")
    if temp_path:
        options["paths"] = {"temp": temp_path}

    if "keep_part" in app_settings:
        options["nopart"] = not _truthy(app_settings.get("keep_part"))

    user_agent = app_settings.get("user_agent")
    if user_agent:
        options["http_headers"] = {"User-Agent": user_agent}

    return options
