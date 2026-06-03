from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DownloadJob:
    url: str
    output_dir: Path
    format_id: str = "bestvideo+bestaudio/best"
    title: str = ""
    container: str = "mp4"
    filename_preset: str = "title"
    skip_existing: bool = True
    audio_only: bool = False
    audio_format: str = "mp3"
    audio_quality: str = "0"
    write_subs: bool = False
    write_auto_subs: bool = True
    embed_subs: bool = False
    subtitle_language: str = ""
    embed_metadata: bool = False
    embed_thumbnail: bool = False
    sponsorblock_mode: str = "off"
    split_chapters: bool = False
    playlist_mode: bool = True
    playlist_items: str = ""
    max_downloads: int | None = None
    live_from_start: bool = False
    wait_for_video: str = ""
