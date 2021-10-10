#!/usr/bin/env python3
# coding: utf-8

from __future__ import unicode_literals
import sys
import platform

from PyInstaller.utils.hooks import collect_submodules

if platform.system() == 'Windows':
    from PyInstaller.utils.win32.versioninfo import (
        VarStruct, VarFileInfo, StringStruct, StringTable,
        StringFileInfo, FixedFileInfo, VSVersionInfo, SetVersion,
    )
import PyInstaller.__main__

suffix = ''
arch = platform.architecture()[0][:2]
assert arch in ('32', '64')
_x86 = '_x86' if arch == '32' else ''

if platform.system() == 'Windows':
    suffix = _x86
if platform.system() == 'Darwin':
    suffix = '_macos'

# Compatability with older arguments
opts = sys.argv[1:]
if opts[0:1] in (['32'], ['64']):
    if arch != opts[0]:
        raise Exception(f'{opts[0]}bit executable cannot be built on a {arch}bit system')
    opts = opts[1:]
opts = opts or ['--onefile']

print(f'Building {arch}bit version with options {opts}')

FILE_DESCRIPTION = 'yt-dlp%s' % (' (32 Bit)' if _x86 else '')

exec(compile(open('yt_dlp/version.py').read(), 'yt_dlp/version.py', 'exec'))
VERSION = locals()['__version__']

VERSION_LIST = VERSION.split('.')
VERSION_LIST = list(map(int, VERSION_LIST)) + [0] * (4 - len(VERSION_LIST))

print('Version: %s%s' % (VERSION, _x86))
print('Remember to update the version using devscipts\\update-version.py')

if platform.system() == 'Windows':
    VERSION_FILE = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=VERSION_LIST,
            prodvers=VERSION_LIST,
            mask=0x3F,
            flags=0x0,
            OS=0x4,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([
                StringTable(
                    '040904B0', [
                        StringStruct('Comments', 'yt-dlp%s Command Line Interface.' % _x86),
                        StringStruct('CompanyName', 'https://github.com/yt-dlp'),
                        StringStruct('FileDescription', FILE_DESCRIPTION),
                        StringStruct('FileVersion', VERSION),
                        StringStruct('InternalName', 'yt-dlp%s' % _x86),
                        StringStruct(
                            'LegalCopyright',
                            'pukkandan.ytdlp@gmail.com | UNLICENSE',
                        ),
                        StringStruct('OriginalFilename', 'yt-dlp%s.exe' % _x86),
                        StringStruct('ProductName', 'yt-dlp%s' % _x86),
                        StringStruct(
                            'ProductVersion',
                            '%s%s on Python %s' % (VERSION, _x86, platform.python_version())),
                    ])]),
            VarFileInfo([VarStruct('Translation', [0, 1200])])
        ]
    )


def pycryptodome_module():
    try:
        import Cryptodome  # noqa: F401
    except ImportError:
        try:
            import Crypto  # noqa: F401
            print('WARNING: Using Crypto since Cryptodome is not available. '
                  'Install with: pip install pycryptodomex', file=sys.stderr)
            return 'Crypto'
        except ImportError:
            pass
    return 'Cryptodome'


dependancies = [pycryptodome_module(), 'mutagen', 'certifi'] + collect_submodules('websockets')
excluded_modules = ['test', 'ytdlp_plugins', 'youtube-dl', 'youtube-dlc']

PyInstaller.__main__.run([
    '--name=yt-dlp%s' % suffix,
    '--icon=devscripts/logo.ico',
    *[f'--exclude-module={module}' for module in excluded_modules],
    *[f'--hidden-import={module}' for module in dependancies],
    '--upx-exclude=vcruntime140.dll',
    '--noconfirm',
    *opts,
    'yt_dlp/__main__.py',
])

if platform.system() == 'Windows':
    SetVersion('dist/%syt-dlp%s.exe' % ('yt-dlp/' if '--onedir' in opts else '', _x86), VERSION_FILE)
