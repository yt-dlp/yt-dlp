"""
yt-dlp Desktop — PyInstaller Entry Point
This script is the entry point for the built .exe.
It sets up paths so all app modules are importable.
"""

import os
import sys


def main():
    # When running as PyInstaller .exe, _MEIPASS is the temp extraction dir
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Add the base dir so 'app' package is importable
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    # Now import and run
    from app.main import main as app_main
    app_main()


if __name__ == '__main__':
    main()
