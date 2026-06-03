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


def test_builds_container_filename_skip_existing_and_chapter_options():
    job = DownloadJob(
        url="https://example.com/video",
        output_dir=Path("C:/Downloads"),
        format_id="bestvideo+bestaudio/best",
        container="mkv",
        filename_preset="uploader-title",
        skip_existing=True,
        split_chapters=True,
    )

    options = build_ydl_options(job, {})

    assert options["merge_output_format"] == "mkv"
    assert options["outtmpl"] == str(Path("C:/Downloads") / "%(uploader).80B - %(title).200B [%(id)s].%(ext)s")
    assert options["overwrites"] is False
    assert options["continuedl"] is True
    assert options["split_chapters"] is True


def test_builds_sponsorblock_playlist_and_live_options():
    job = DownloadJob(
        url="https://example.com/playlist",
        output_dir=Path("C:/Downloads"),
        format_id="best",
        sponsorblock_mode="skip",
        playlist_mode=True,
        playlist_items="1:5",
        max_downloads=3,
        live_from_start=True,
        wait_for_video="30-120",
    )

    options = build_ydl_options(job, {})

    assert options["sponsorblock_remove"] == {"sponsor"}
    assert options["noplaylist"] is False
    assert options["playlist_items"] == "1:5"
    assert options["max_downloads"] == 3
    assert options["live_from_start"] is True
    assert options["wait_for_video"] == "30-120"


def test_builds_config_power_user_options():
    job = DownloadJob(
        url="https://example.com/video",
        output_dir=Path("C:/Downloads"),
        format_id="best",
    )
    settings = {
        "concurrent_fragments": "4",
        "retries": "15",
        "download_archive": "C:/Downloads/archive.txt",
        "impersonate": "chrome:windows-10",
        "force_ip": "ipv4",
        "socket_timeout": "30",
        "cookies_from_browser": "firefox",
        "paths_temp": "C:/Temp/YTStudio",
        "keep_part": "true",
    }

    options = build_ydl_options(job, settings)

    assert options["concurrent_fragment_downloads"] == 4
    assert options["retries"] == 15
    assert options["download_archive"] == "C:/Downloads/archive.txt"
    assert options["impersonate"] == "chrome:windows-10"
    assert options["force_ipv4"] is True
    assert options["socket_timeout"] == 30
    assert options["cookiesfrombrowser"] == ("firefox", None, None, None)
    assert options["paths"]["temp"] == "C:/Temp/YTStudio"
    assert options["nopart"] is False
