from pathlib import Path

from core.models import DownloadJob
from core.options import build_ydl_options


def test_builds_video_options_with_format_and_output_template():
    job = DownloadJob(
        url="https://example.com/video",
        output_dir=Path("C:/Downloads"),
        format_id="bestvideo[height<=1080]+bestaudio/best",
    )

    options = build_ydl_options(job, {})

    assert options["format"] == "bestvideo[height<=1080]+bestaudio/best"
    assert options["outtmpl"] == str(Path("C:/Downloads") / "%(title).200B [%(id)s].%(ext)s")
    assert options["noplaylist"] is False


def test_builds_audio_options_with_extract_audio_postprocessor():
    job = DownloadJob(
        url="https://example.com/video",
        output_dir=Path("C:/Downloads"),
        format_id="bestaudio/best",
        audio_only=True,
        audio_format="mp3",
    )

    options = build_ydl_options(job, {})

    assert options["format"] == "bestaudio/best"
    assert {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"} in options["postprocessors"]


def test_builds_subtitle_metadata_thumbnail_and_network_options():
    job = DownloadJob(
        url="https://example.com/video",
        output_dir=Path("C:/Downloads"),
        format_id="best",
        write_subs=True,
        embed_subs=True,
        subtitle_language="en,ar",
        embed_metadata=True,
        embed_thumbnail=True,
    )
    settings = {
        "cookies_file": "C:/cookies.txt",
        "proxy": "socks5://127.0.0.1:9050",
        "rate_limit": "1M",
        "user_agent": "YT-Studio Test",
        "ffmpeg_location": "C:/ffmpeg/bin",
    }

    options = build_ydl_options(job, settings)

    assert options["writesubtitles"] is True
    assert options["writeautomaticsub"] is True
    assert options["subtitleslangs"] == ["en", "ar"]
    assert options["embedsubtitles"] is True
    assert options["cookiefile"] == "C:/cookies.txt"
    assert options["proxy"] == "socks5://127.0.0.1:9050"
    assert options["ratelimit"] == "1M"
    assert options["http_headers"]["User-Agent"] == "YT-Studio Test"
    assert options["ffmpeg_location"] == "C:/ffmpeg/bin"
    assert {"key": "FFmpegMetadata", "add_metadata": True} in options["postprocessors"]
    assert {"key": "EmbedThumbnail"} in options["postprocessors"]
