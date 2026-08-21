#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import sysconfig

from PyInstaller.__main__ import run as run_pyinstaller

from bundle.pyinstaller import (
    OS_NAME,
    announce,
    base_options,
    exe,
    parse_options,
    resolve_onedir,
    set_version_info,
)
from devscripts.utils import read_version

BASE_NAME = 'yt-dlp-gui'
BUNDLE_IDENTIFIER = 'org.yt-dlp.gui'
ICNS_PATH = 'build/yt-dlp-gui.icns'
RUNTIME_NAME = 'deno'
RUNTIME_STAGE = 'build/runtime'


def runtime_options():
    """Bundle the JavaScript runtime where a frozen yt-dlp looks for it

    A frozen application reports its own directory as `sys.prefix`, so placing
    the binary in the interpreter "scripts" path makes it discoverable without
    the user installing anything.
    """
    scripts_dir = sysconfig.get_path('scripts')
    binary = RUNTIME_NAME + sysconfig.get_config_var('EXE')
    source = os.path.join(scripts_dir, binary)
    if not os.path.isfile(source):
        print(f'WARNING: {binary} was not found in {scripts_dir}. The bundle will require a '
              'JavaScript runtime to be installed separately', file=sys.stderr)
        return []

    os.makedirs(RUNTIME_STAGE, exist_ok=True)
    staged = os.path.join(RUNTIME_STAGE, binary)
    shutil.copy2(source, staged)
    destination = 'Scripts' if OS_NAME == 'win32' else 'bin'
    return [f'--add-binary={staged}:{destination}']


def main():
    opts, version = parse_options(), read_version()
    onedir = resolve_onedir(opts)

    name, final_file = exe(onedir, BASE_NAME)
    announce(BASE_NAME, version, final_file, opts)

    windowed, icon = ['--windowed'], 'devscripts/logo.ico'
    if OS_NAME == 'darwin':
        from devscripts.make_gui_icons import write_icns

        windowed.append(f'--osx-bundle-identifier={BUNDLE_IDENTIFIER}')
        icon = write_icns(ICNS_PATH)

    opts = [*base_options(name, icon), *windowed, *runtime_options(), *opts, 'yt_dlp/gui/__main__.py']

    print(f'Running PyInstaller with {opts}')
    run_pyinstaller(opts)
    set_version_info(final_file, version, BASE_NAME, 'Graphical Interface')


if __name__ == '__main__':
    main()
