from collections.abc import Callable
from pathlib import Path

from core.models import DownloadJob
from core.options import build_ydl_options
from core.qt_compat import QThread, Signal


class DownloadWorker(QThread):
    progress = Signal(dict)
    status = Signal(str)
    error = Signal(str)
    finished = Signal(dict)
    canceled = Signal()

    def __init__(
        self,
        job: DownloadJob,
        app_settings: dict[str, str] | None = None,
        youtube_dl_factory: Callable | None = None,
    ):
        super().__init__()
        self.job = job
        self.app_settings = app_settings or {}
        self._youtube_dl_factory = youtube_dl_factory
        self._cancel_requested = False
        self._download_finished_seen = False
        self._last_downloaded_filename = ""

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        try:
            if self._cancel_requested:
                self.canceled.emit()
                return

            options = build_ydl_options(self.job, self.app_settings)
            options["progress_hooks"] = [self._progress_hook]

            if self._youtube_dl_factory is None:
                import yt_dlp

                factory = yt_dlp.YoutubeDL
            else:
                factory = self._youtube_dl_factory

            self.status.emit("Starting download...")
            with factory(options) as ydl:
                ydl.download([self.job.url])
            if self._cancel_requested:
                self.canceled.emit()
            else:
                self.finished.emit({"url": self.job.url, "title": self.job.title})
        except Exception as exc:
            if self._should_keep_completed_download(str(exc)):
                self.finished.emit({
                    "url": self.job.url,
                    "title": self.job.title,
                    "filename": self._last_downloaded_filename,
                    "warning": str(exc),
                })
                return
            self.error.emit(str(exc))

    def _progress_hook(self, data: dict):
        if self._cancel_requested:
            raise RuntimeError("Download canceled")

        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100) if total else 0.0
            self.progress.emit(
                {
                    "percent": round(percent, 2),
                    "speed": data.get("speed"),
                    "eta": data.get("eta"),
                    "filename": data.get("filename", ""),
                }
            )
        elif data.get("status") == "finished":
            filename = data.get("filename", "")
            self._download_finished_seen = True
            self._last_downloaded_filename = filename
            self.status.emit(f"Finished downloading {filename}; post-processing if needed.")

    def _last_finished_file_exists(self) -> bool:
        if not self._last_downloaded_filename:
            return False
        return Path(self._last_downloaded_filename).exists()

    def _should_keep_completed_download(self, message: str) -> bool:
        if not self._download_finished_seen:
            return False
        if self._last_finished_file_exists():
            return True
        normalized = message.lower()
        return "postprocessing" in normalized or "error opening output files" in normalized
