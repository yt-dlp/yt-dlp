from collections.abc import Callable

from core.qt_compat import QThread, Signal


class InfoWorker(QThread):
    fetched = Signal(dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, ydl_options: dict | None = None, youtube_dl_factory: Callable | None = None):
        super().__init__()
        self.url = url
        self.ydl_options = ydl_options or {}
        self._youtube_dl_factory = youtube_dl_factory

    def run(self):
        try:
            options = {
                "quiet": True,
                "skip_download": True,
                "extract_flat": False,
                **self.ydl_options,
            }
            if self._youtube_dl_factory is None:
                import yt_dlp

                factory = yt_dlp.YoutubeDL
            else:
                factory = self._youtube_dl_factory
            with factory(options) as ydl:
                info = ydl.extract_info(self.url, download=False)
            self.fetched.emit(info)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()
