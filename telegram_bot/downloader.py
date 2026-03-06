import asyncio
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

import shutil

from config import (
    COOKIES_FILE,
    DOWNLOAD_DIR,
    DOWNLOAD_TIMEOUT,
    MAX_FILE_SIZE_BYTES,
    PROXY_URL,
    USE_ARIA2C,
    USE_SPONSORBLOCK,
)

logger = logging.getLogger(__name__)


class _DownloadCancelled(BaseException):
    """Поднимается из progress-хука для прерывания загрузки.

    Наследует BaseException, а не Exception — yt-dlp использует
    `except Exception` внутри, поэтому только BaseException гарантированно
    пробьётся через все обёртки yt-dlp и отменит загрузку немедленно.
    """


# ── Data classes ────────────────────────────────────────────────────────────────

@dataclass
class FormatInfo:
    format_id: str
    ext: str
    quality: str
    resolution: str
    fps: Optional[int]
    vcodec: str
    acodec: str
    filesize: Optional[int]
    tbr: Optional[float]  # total bitrate kbps
    note: str = ""

    @property
    def is_video(self) -> bool:
        return self.vcodec not in ("none", "", None)

    @property
    def is_audio_only(self) -> bool:
        return not self.is_video and self.acodec not in ("none", "", None)

    @property
    def size_str(self) -> str:
        if self.filesize:
            mb = self.filesize / (1024 * 1024)
            return f"{mb:.1f} MB"
        if self.tbr:
            return f"~{self.tbr:.0f} kbps"
        return "unknown"

    @property
    def label(self) -> str:
        parts = []
        if self.resolution and self.resolution != "audio only":
            parts.append(self.resolution)
        if self.fps:
            parts.append(f"{self.fps}fps")
        parts.append(self.ext.upper())
        parts.append(f"[{self.size_str}]")
        return " · ".join(parts)


@dataclass
class VideoInfo:
    url: str
    title: str
    uploader: str
    duration: int  # seconds
    view_count: int
    like_count: Optional[int]
    thumbnail: str
    description: str
    formats: list[FormatInfo] = field(default_factory=list)
    is_playlist: bool = False
    playlist_count: Optional[int] = None
    webpage_url: str = ""
    extractor: str = ""

    @property
    def duration_str(self) -> str:
        h, r = divmod(self.duration or 0, 3600)
        m, s = divmod(r, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @property
    def views_str(self) -> str:
        v = self.view_count or 0
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v/1_000:.1f}K"
        return str(v)


@dataclass
class DownloadResult:
    success: bool
    file_path: Optional[Path] = None
    title: str = ""
    file_size: int = 0
    error: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _base_opts() -> dict:
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
    }
    if PROXY_URL:
        opts["proxy"] = PROXY_URL
    if COOKIES_FILE and Path(COOKIES_FILE).exists():
        opts["cookiefile"] = COOKIES_FILE
    # aria2c: параллельные соединения (до 16) — ускоряет HTTP-загрузки
    if USE_ARIA2C and shutil.which("aria2c"):
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = {"default": ["-x16", "-s16", "-k1M", "--quiet"]}
    return opts


def _human_size(n: Optional[int]) -> str:
    if not n:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ── Info extraction ─────────────────────────────────────────────────────────────

async def get_video_info(url: str) -> VideoInfo:
    """Extract metadata + available formats (no download)."""
    opts = _base_opts()
    opts.update({
        "skip_download": True,
        "extract_flat": False,
    })

    loop = asyncio.get_running_loop()

    def _extract():
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    info = await loop.run_in_executor(None, _extract)

    is_playlist = info.get("_type") == "playlist"
    if is_playlist:
        # Return minimal playlist info
        entries = info.get("entries") or []
        return VideoInfo(
            url=url,
            title=info.get("title", "Playlist"),
            uploader=info.get("uploader", ""),
            duration=0,
            view_count=0,
            like_count=None,
            thumbnail=info.get("thumbnail", ""),
            description="",
            is_playlist=True,
            playlist_count=len(entries),
            webpage_url=info.get("webpage_url", url),
            extractor=info.get("extractor", ""),
        )

    formats = _parse_formats(info.get("formats") or [])

    return VideoInfo(
        url=url,
        title=info.get("title", ""),
        uploader=info.get("uploader", ""),
        duration=info.get("duration", 0),
        view_count=info.get("view_count", 0),
        like_count=info.get("like_count"),
        thumbnail=info.get("thumbnail", ""),
        description=(info.get("description") or "")[:500],
        formats=formats,
        webpage_url=info.get("webpage_url", url),
        extractor=info.get("extractor", ""),
    )


def _parse_formats(raw_formats: list) -> list[FormatInfo]:
    seen = set()
    result = []

    for f in raw_formats:
        fid = f.get("format_id", "")
        vcodec = f.get("vcodec", "none") or "none"
        acodec = f.get("acodec", "none") or "none"
        ext = f.get("ext", "")
        height = f.get("height")
        width = f.get("width")
        fps = f.get("fps")
        tbr = f.get("tbr")
        filesize = f.get("filesize") or f.get("filesize_approx")

        # Determine resolution label
        if height:
            res = f"{height}p"
        elif width:
            res = f"{width}w"
        elif vcodec == "none":
            res = "audio only"
        else:
            res = "unknown"

        quality = f.get("quality", 0) or 0

        # Skip duplicate resolutions for video formats (keep best tbr)
        dedup_key = (res, ext, vcodec != "none", acodec != "none")
        if dedup_key in seen and res != "audio only":
            continue
        seen.add(dedup_key)

        # Skip storyboard/mhtml
        if ext in ("mhtml", "none"):
            continue
        if "storyboard" in fid.lower():
            continue

        result.append(FormatInfo(
            format_id=fid,
            ext=ext,
            quality=str(quality),
            resolution=res,
            fps=int(fps) if fps else None,
            vcodec=vcodec,
            acodec=acodec,
            filesize=filesize,
            tbr=tbr,
            note=f.get("format_note", ""),
        ))

    # Sort: video by height desc, then audio
    def sort_key(f: FormatInfo):
        if f.is_audio_only:
            return (0, f.tbr or 0)
        try:
            h = int(f.resolution.rstrip("p"))
        except (ValueError, AttributeError):
            h = 0
        return (1, h)

    result.sort(key=sort_key, reverse=True)
    return result


def get_best_video_formats(formats: list[FormatInfo]) -> list[FormatInfo]:
    """Return unique video+audio combined formats for user selection."""
    video_formats = [f for f in formats if f.is_video]
    # Deduplicate by resolution
    seen_res = set()
    unique = []
    for f in video_formats:
        if f.resolution not in seen_res:
            seen_res.add(f.resolution)
            unique.append(f)
    return unique[:8]  # Limit to 8 options


def get_audio_formats(formats: list[FormatInfo]) -> list[FormatInfo]:
    return [f for f in formats if f.is_audio_only][:5]


# ── Download ────────────────────────────────────────────────────────────────────

class ProgressTracker:
    def __init__(self, callback: Optional[Callable] = None, loop=None):
        self.callback = callback
        self.loop = loop
        self.downloaded = 0
        self.total = 0
        self.speed = 0
        self.eta = 0
        self.status = "downloading"
        self._last_update = 0.0

    def hook(self, d: dict) -> None:
        self.status = d.get("status", "")
        if self.status == "downloading":
            self.downloaded = d.get("downloaded_bytes", 0)
            self.total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            self.speed = d.get("speed", 0) or 0
            self.eta = d.get("eta", 0) or 0
            if self.callback and self.loop:
                now = time.monotonic()
                if now - self._last_update >= 5.0:   # не чаще раза в 5 секунд
                    self._last_update = now
                    asyncio.run_coroutine_threadsafe(self.callback(self), self.loop)


async def download_video(
    url: str,
    format_id: str,
    output_dir: Path,
    progress_callback: Optional[Callable] = None,
    audio_only: bool = False,
    subtitle_lang: Optional[str] = None,
    cancel_flag: Optional[list] = None,
) -> DownloadResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title).80s.%(ext)s")

    opts = _base_opts()
    loop = asyncio.get_running_loop()
    tracker = ProgressTracker(progress_callback, loop)

    def _cancel_hook(d: dict) -> None:
        """Вызывается из yt-dlp прогресс-хука.

        Поднимаем _DownloadCancelled (BaseException), чтобы пробить
        все `except Exception` внутри yt-dlp и немедленно прервать загрузку.
        """
        if cancel_flag and cancel_flag[0]:
            raise _DownloadCancelled("CANCELLED")

    if audio_only:
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        # Combine selected video with best audio
        if format_id and format_id != "best":
            fmt = f"{format_id}+bestaudio/best[height<={_height_from_fid(format_id)}]/best"
        else:
            fmt = "bestvideo+bestaudio/best"
        opts["format"] = fmt
        opts["merge_output_format"] = "mp4"

    if subtitle_lang:
        opts.update({
            "writesubtitles": True,
            "subtitleslangs": [subtitle_lang],
            "writeautomaticsub": True,
        })

    # SponsorBlock: автоматически вырезать рекламные вставки из YouTube
    if USE_SPONSORBLOCK and not audio_only:
        opts["sponsorblock_remove"] = ["sponsor", "selfpromo", "interaction"]

    hooks = [tracker.hook, _cancel_hook]
    opts.update({
        "outtmpl": output_template,
        "progress_hooks": hooks,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "file_access_retries": 3,
        "noplaylist": True,
    })

    result_holder = {}

    def _download():
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                # Handle post-processing extension change (e.g. mp3)
                if audio_only:
                    filename = Path(filename).with_suffix(".mp3")
                else:
                    filename = Path(filename).with_suffix(".mp4")
                    if not filename.exists():
                        # Try original
                        filename = Path(ydl.prepare_filename(info))

                result_holder["title"] = info.get("title", "")
                result_holder["file_path"] = Path(filename)
        except _DownloadCancelled:
            # Отмена пользователем — не логируем как ошибку
            result_holder["error"] = "CANCELLED"
        except Exception as e:
            result_holder["error"] = str(e)

    try:
        await asyncio.wait_for(
            loop.run_in_executor(None, _download),
            timeout=DOWNLOAD_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return DownloadResult(success=False, error="Download timed out")

    if "error" in result_holder:
        if cancel_flag and cancel_flag[0]:
            return DownloadResult(success=False, error="CANCELLED")
        return DownloadResult(success=False, error=result_holder["error"])

    if cancel_flag and cancel_flag[0]:
        return DownloadResult(success=False, error="CANCELLED")

    file_path: Path = result_holder.get("file_path")
    if not file_path or not file_path.exists():
        # Try to find the downloaded file
        candidates = sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            file_path = candidates[0]
        else:
            return DownloadResult(success=False, error="Downloaded file not found")

    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        file_path.unlink(missing_ok=True)
        return DownloadResult(
            success=False,
            error=f"File too large: {_human_size(file_size)} (max {_human_size(MAX_FILE_SIZE_BYTES)})",
        )

    return DownloadResult(
        success=True,
        file_path=file_path,
        title=result_holder.get("title", ""),
        file_size=file_size,
    )


async def download_playlist(
    url: str,
    format_id: str,
    output_dir: Path,
    max_items: int = 10,
) -> list[DownloadResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = _base_opts()
    if format_id == "bestaudio":
        fmt = "bestaudio/best"
    elif format_id != "best":
        fmt = f"{format_id}+bestaudio/best"
    else:
        fmt = "bestvideo+bestaudio/best"
    opts.update({
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(playlist_index)s-%(title).60s.%(ext)s"),
        "noplaylist": False,
        "playlistend": max_items,
        "socket_timeout": 30,
        "retries": 3,
    })

    loop = asyncio.get_running_loop()
    results = []

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    await loop.run_in_executor(None, _download)

    for f in sorted(output_dir.iterdir()):
        if f.is_file() and f.suffix in (".mp4", ".webm", ".mkv", ".mp3"):
            size = f.stat().st_size
            results.append(DownloadResult(
                success=True,
                file_path=f,
                title=f.stem,
                file_size=size,
            ))
    return results


def _height_from_fid(format_id: str) -> int:
    """Best-effort: if format_id encodes height, extract it."""
    m = re.search(r"(\d{3,4})p?", format_id)
    return int(m.group(1)) if m else 9999


_EXTRACTORS: list | None = None


def is_supported_url(url: str) -> bool:
    """Проверяет URL без инстанциирования всех экстракторов каждый раз."""
    global _EXTRACTORS
    if _EXTRACTORS is None:
        _EXTRACTORS = list(yt_dlp.extractor.gen_extractors())
    for e in _EXTRACTORS:
        if e.suitable(url) and e.IE_NAME != "generic":
            return True
    # Любой http(s) URL допускаем (generic extractor)
    return bool(re.match(r"https?://", url))
