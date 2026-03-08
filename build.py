"""
Build script for yt-dlp Desktop Application.
Creates a standalone .exe using PyInstaller.

Usage:
    python build.py
"""

import os
import subprocess
import sys


def build():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(root_dir, 'app')
    static_dir = os.path.join(app_dir, 'static')
    icon_path = os.path.join(static_dir, 'logo.ico')
    launcher = os.path.join(root_dir, 'launcher.py')

    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print('[Build] Installing PyInstaller...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # Build command — use launcher.py as entry, bundle the whole app/ package
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=yt-dlp-Desktop',
        '--onefile',
        '--windowed',
        f'--icon={icon_path}',
        # Bundle the entire app/ package as a proper Python package
        f'--add-data={app_dir};app',
        # Hidden imports for the app package and its dependencies
        '--hidden-import=app',
        '--hidden-import=app.main',
        '--hidden-import=app.api',
        '--hidden-import=app.bootstrap',
        '--hidden-import=webview',
        '--hidden-import=clr_loader',
        '--hidden-import=pythonnet',
        '--hidden-import=bottle',
        '--hidden-import=proxy_tools',
        '--hidden-import=yt_dlp',
        '--collect-all=webview',
        '--collect-all=clr_loader',
        '--collect-all=pythonnet',
        '--noconfirm',
        '--clean',
        launcher,
    ]

    print('[Build] Building yt-dlp Desktop .exe ...')
    print(f'[Build] Entry: {launcher}')
    print(f'[Build] Icon:  {icon_path}')

    subprocess.check_call(cmd)

    print()
    print('=' * 50)
    print('  BUILD COMPLETE!')
    print('  Output: dist/yt-dlp-Desktop.exe')
    print('=' * 50)


if __name__ == '__main__':
    build()
