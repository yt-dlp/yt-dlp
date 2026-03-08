"""
yt-dlp Desktop Application — Entry Point
Launches a native window with the web-based UI.
Runs bootstrap checks on startup (deps, FFmpeg, updates).
"""

import os
import sys
import threading


def main():
    # Run bootstrap BEFORE importing webview (it may install it)
    from . import bootstrap
    bootstrap.bootstrap()

    import webview
    from .api import Api

    api = Api()

    # Path to the static HTML file — handle both dev and PyInstaller paths
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        static_dir = os.path.join(base_dir, 'app', 'static')
    else:
        static_dir = os.path.join(os.path.dirname(__file__), 'static')

    html_path = os.path.join(static_dir, 'index.html')
    icon_path = os.path.join(static_dir, 'logo.ico')

    if not os.path.exists(html_path):
        print(f'ERROR: UI file not found at {html_path}')
        sys.exit(1)

    window = webview.create_window(
        title='yt-dlp Desktop',
        url=html_path,
        js_api=api,
        width=1100,
        height=750,
        min_size=(800, 600),
        background_color='#0a0a0f',
        frameless=False,
        easy_drag=False,
        text_select=False,
    )

    api.set_window(window)

    def on_loaded():
        """After UI loads, install FFmpeg in background if missing."""
        if not bootstrap.find_ffmpeg():
            threading.Thread(target=bootstrap.install_ffmpeg, daemon=True).start()

    window.events.loaded += on_loaded

    # Start with the yt-dlp icon
    start_kwargs = {'debug': False}
    if os.path.isfile(icon_path):
        start_kwargs['icon'] = icon_path

    webview.start(**start_kwargs)


if __name__ == '__main__':
    main()
