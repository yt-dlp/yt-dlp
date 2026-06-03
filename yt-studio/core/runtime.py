import sys
from pathlib import Path


def app_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def bundled_ffmpeg_path() -> Path | None:
    for candidate in (
        app_base_path() / "assets" / "ffmpeg.exe",
        Path(sys.executable).resolve().parent / "assets" / "ffmpeg.exe",
    ):
        if candidate.exists():
            return candidate
    return None
