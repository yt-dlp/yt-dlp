import sys
from os import environ
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def resolve_ytdlp_source(app_root: Path = ROOT) -> Path | None:
    configured = environ.get("YT_STUDIO_YTDLP_SOURCE")
    candidates = [
        Path(configured) if configured else None,
        app_root.parent,
        app_root.parent / "yt-dlp-publish",
        app_root.parent / "yt-dlp-2026.03.17" / "yt-dlp-2026.03.17",
    ]
    for candidate in candidates:
        if candidate and (candidate / "yt_dlp").is_dir():
            return candidate
    return None


def install_ytdlp_source(app_root: Path = ROOT) -> Path | None:
    source = resolve_ytdlp_source(app_root)
    if source:
        sys.path.insert(0, str(source))
    return source


def main() -> int:
    install_ytdlp_source()

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("YT-Studio")
    app.setFont(QFont("Courier New", 10))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
