from pathlib import Path

from core.models import DownloadJob


def _split_languages(value: str) -> list[str]:
    return [language.strip() for language in value.split(",") if language.strip()]


def build_ydl_options(job: DownloadJob, app_settings: dict[str, str]) -> dict:
    outtmpl = str(Path(job.output_dir) / "%(title).200B [%(id)s].%(ext)s")
    postprocessors = []

    options = {
        "format": job.format_id or "bestvideo+bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": False,
        "progress_hooks": [],
    }

    if job.audio_only:
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": job.audio_format or "mp3",
                "preferredquality": "0",
            }
        )

    if job.write_subs:
        options["writesubtitles"] = True
        options["writeautomaticsub"] = True
        options["subtitleslangs"] = _split_languages(job.subtitle_language) or ["en"]

    if job.embed_subs:
        options["embedsubtitles"] = True

    if job.embed_metadata:
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})

    if job.embed_thumbnail:
        options["writethumbnail"] = True
        postprocessors.append({"key": "EmbedThumbnail"})

    if postprocessors:
        options["postprocessors"] = postprocessors

    settings_to_options = {
        "cookies_file": "cookiefile",
        "proxy": "proxy",
        "rate_limit": "ratelimit",
        "ffmpeg_location": "ffmpeg_location",
    }
    for setting_key, option_key in settings_to_options.items():
        value = app_settings.get(setting_key)
        if value:
            options[option_key] = value

    user_agent = app_settings.get("user_agent")
    if user_agent:
        options["http_headers"] = {"User-Agent": user_agent}

    return options
