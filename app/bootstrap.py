"""
yt-dlp Desktop Application — Bootstrap & Auto-Updater
Handles automatic dependency installation and yt-dlp self-update.
"""

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
import tempfile


def _log(msg):
    """Print a bootstrap message."""
    try:
        print(f'[yt-dlp Desktop] {msg}')
    except UnicodeEncodeError:
        # Fallback if console can't print special chars
        print(f'[yt-dlp Desktop] {msg.encode("ascii", "ignore").decode("ascii")}')


# ============================================
# Python Dependency Check & Install
# ============================================

REQUIRED_PACKAGES = {
    'webview': 'pywebview',
}


def check_python_deps():
    """Check and install missing Python dependencies."""
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        _log(f'Installing missing packages: {", ".join(missing)}')
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '--quiet'] + missing,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _log('Python dependencies installed successfully.')
            return True
        except subprocess.CalledProcessError as e:
            _log(f'Failed to install packages: {e}')
            return False
    return True


# ============================================
# FFmpeg Auto-Install
# ============================================

FFMPEG_INSTALL_DIR = os.path.join(os.path.dirname(__file__), 'ffmpeg')
FFMPEG_DOWNLOAD_URL = (
    'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
    'ffmpeg-master-latest-win64-gpl.zip'
)


def find_ffmpeg():
    """Find FFmpeg — checks bundled dir, PATH, then common install locations."""
    # 1. Check bundled ffmpeg (our own install)
    bundled = os.path.join(FFMPEG_INSTALL_DIR, 'bin', 'ffmpeg.exe')
    if os.path.isfile(bundled):
        return os.path.join(FFMPEG_INSTALL_DIR, 'bin')

    # Also check flat structure
    bundled_flat = os.path.join(FFMPEG_INSTALL_DIR, 'ffmpeg.exe')
    if os.path.isfile(bundled_flat):
        return FFMPEG_INSTALL_DIR

    # 2. Check PATH
    path_ffmpeg = shutil.which('ffmpeg')
    if path_ffmpeg:
        return os.path.dirname(path_ffmpeg)

    # 3. Search common Windows install locations
    search_dirs = []
    local_app = os.environ.get('LOCALAPPDATA', '')
    home = os.path.expanduser('~')

    if local_app:
        winget_dir = os.path.join(local_app, 'Microsoft', 'WinGet', 'Packages')
        if os.path.isdir(winget_dir):
            search_dirs.append(winget_dir)

    for base in [r'C:\ffmpeg', r'C:\Program Files\ffmpeg', r'C:\tools\ffmpeg',
                 os.path.join(home, 'ffmpeg'), os.path.join(home, 'scoop', 'shims')]:
        if os.path.isdir(base):
            search_dirs.append(base)

    choco = r'C:\ProgramData\chocolatey\bin'
    if os.path.isdir(choco) and os.path.isfile(os.path.join(choco, 'ffmpeg.exe')):
        return choco

    for search_dir in search_dirs:
        for root, dirs, files in os.walk(search_dir):
            if 'ffmpeg.exe' in files:
                return root

    return None


def install_ffmpeg(progress_callback=None):
    """Download and install FFmpeg automatically."""
    if find_ffmpeg():
        return True

    if platform.system() != 'Windows':
        _log('Auto-install of FFmpeg only supported on Windows. Please install FFmpeg manually.')
        return False

    _log('Downloading FFmpeg...')

    try:
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, 'ffmpeg.zip')

        # Download with progress
        def _reporthook(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                downloaded = block_num * block_size
                pct = min(100, downloaded * 100 / total_size)
                progress_callback(f'Downloading FFmpeg... {pct:.0f}%')

        urllib.request.urlretrieve(FFMPEG_DOWNLOAD_URL, zip_path, _reporthook)
        _log('Extracting FFmpeg...')

        if progress_callback:
            progress_callback('Extracting FFmpeg...')

        # Extract
        os.makedirs(FFMPEG_INSTALL_DIR, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Find the bin directory inside the zip
            bin_files = [f for f in zf.namelist()
                         if '/bin/' in f and f.endswith(('.exe', '.dll'))]

            for file_info in bin_files:
                filename = os.path.basename(file_info)
                if not filename:
                    continue
                bin_dir = os.path.join(FFMPEG_INSTALL_DIR, 'bin')
                os.makedirs(bin_dir, exist_ok=True)
                target = os.path.join(bin_dir, filename)
                with zf.open(file_info) as src, open(target, 'wb') as dst:
                    dst.write(src.read())

        # Cleanup
        shutil.rmtree(tmp_dir, ignore_errors=True)

        if find_ffmpeg():
            _log('FFmpeg installed successfully.')
            if progress_callback:
                progress_callback('FFmpeg installed!')
            return True
        else:
            _log('FFmpeg extraction failed.')
            return False

    except Exception as e:
        _log(f'Failed to download FFmpeg: {e}')
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False


# ============================================
# yt-dlp Self-Update
# ============================================

YTDLP_PYPI_URL = 'https://pypi.org/pypi/yt-dlp/json'


def get_current_version():
    """Get the currently installed yt-dlp version."""
    try:
        from yt_dlp.version import __version__
        return __version__
    except ImportError:
        return None


def get_latest_version():
    """Check PyPI for the latest yt-dlp version."""
    try:
        req = urllib.request.Request(YTDLP_PYPI_URL, headers={
            'User-Agent': 'yt-dlp-desktop/1.0',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get('info', {}).get('version')
    except Exception:
        return None


def check_update_available():
    """Check if a yt-dlp update is available."""
    current = get_current_version()
    latest = get_latest_version()
    if current and latest and current != latest:
        return {'current': current, 'latest': latest, 'available': True}
    return {'current': current, 'latest': latest, 'available': False}


def update_ytdlp():
    """Update yt-dlp to the latest version."""
    _log('Updating yt-dlp...')
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', '--quiet', 'yt-dlp'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log('yt-dlp updated successfully.')
        return True
    except subprocess.CalledProcessError as e:
        _log(f'Failed to update yt-dlp: {e}')
        return False


# ============================================
# Bootstrap (run on startup)
# ============================================

def bootstrap():
    """Run all startup checks."""
    _log('Starting bootstrap...')

    # 1. Check Python dependencies
    check_python_deps()

    # 2. Check FFmpeg
    if not find_ffmpeg():
        _log('FFmpeg not found. Will download on first use or in background.')

    # 3. Check for yt-dlp updates (non-blocking info)
    update_info = check_update_available()
    if update_info['available']:
        _log(f'yt-dlp update available: {update_info["current"]} -> {update_info["latest"]}')

    _log('Bootstrap complete.')
    return update_info


if __name__ == '__main__':
    bootstrap()
