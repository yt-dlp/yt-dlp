from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DownloadJob:
    url: str
    output_dir: Path
    format_id: str = "bestvideo+bestaudio/best"
    title: str = ""
    audio_only: bool = False
    audio_format: str = "mp3"
    write_subs: bool = False
    embed_subs: bool = False
    subtitle_language: str = ""
    embed_metadata: bool = False
    embed_thumbnail: bool = False
