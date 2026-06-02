import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
YTDLP_SOURCE = ROOT.parent / "yt-dlp-2026.03.17" / "yt-dlp-2026.03.17"
if YTDLP_SOURCE.exists():
    sys.path.insert(0, str(YTDLP_SOURCE))


from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("YT-Studio")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
