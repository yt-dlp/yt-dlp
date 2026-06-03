# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


block_cipher = None
root = Path.cwd()
engine_candidates = (
    root.parent,
    root.parent / "yt-dlp-publish",
    root.parent / "yt-dlp-2026.03.17" / "yt-dlp-2026.03.17",
)
engine_source = next((candidate for candidate in engine_candidates if (candidate / "yt_dlp").is_dir()), None)
pathex = [str(root)]
hookspath = []
if engine_source:
    sys.path.insert(0, str(engine_source))
    pathex.insert(0, str(engine_source))
    yt_dlp_hooks = engine_source / "yt_dlp" / "__pyinstaller"
    if yt_dlp_hooks.is_dir():
        hookspath.append(str(yt_dlp_hooks))

assets = root / "assets"
datas = []
ffmpeg = assets / "ffmpeg.exe"
if ffmpeg.exists():
    datas.append((str(ffmpeg), "assets"))


a = Analysis(
    ["main.py"],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("yt_dlp"),
    hookspath=hookspath,
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="YTStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
