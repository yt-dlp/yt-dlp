#!/usr/bin/env python3
# coding: utf-8
import os
import platform
import sys
from PyInstaller.utils.hooks import collect_submodules


OS_NAME = platform.system()
if OS_NAME == 'Windows':
    from PyInstaller.utils.win32.versioninfo import (
        VarStruct, VarFileInfo, StringStruct, StringTable,
        StringFileInfo, FixedFileInfo, VSVersionInfo, SetVersion,
    )
elif OS_NAME == 'Darwin':
    pass
else:
    raise Exception('{OS_NAME} is not supported')

ARCH = platform.architecture()[0][:2]


def main():
    opts = parse_options()
    version = read_version()

    suffix = '_macos' if OS_NAME == 'Darwin' else '_x86' if ARCH == '32' else ''
    final_file = 'dist/%syt-dlp%s%s' % (
        'yt-dlp/' if '--onedir' in opts else '', suffix, '.exe' if OS_NAME == 'Windows' else '')

    print(f'Building yt-dlp v{version} {ARCH}bit for {OS_NAME} with options {opts}')
    print('Remember to update the version using  "devscripts/update-version.py"')
    if not os.path.isfile('yt_dlp/extractor/lazy_extractors.py'):
        print('WARNING: Building without lazy_extractors. Run  '
              '"devscripts/make_lazy_extractors.py"  to build lazy extractors', file=sys.stderr)
    print(f'Destination: {final_file}\n')

    opts = [
        f'--name=yt-dlp{suffix}',
        '--icon=devscripts/logo.ico',
        '--upx-exclude=vcruntime140.dll',
        '--noconfirm',
        *dependancy_options(),
        *opts,
        'yt_dlp/__main__.py',
    ]
    print(f'Running PyInstaller with {opts}')

    import PyInstaller.__main__

    PyInstaller.__main__.run(opts)

    set_version_info(final_file, version)


def parse_options():
    # Compatability with older arguments
    opts = sys.argv[1:]
    if opts[0:1] in (['32'], ['64']):
        if ARCH != opts[0]:
            raise Exception(f'{opts[0]}bit executable cannot be built on a {ARCH}bit system')
        opts = opts[1:]
    return opts or ['--onefile']


def read_version():
    exec(compile(open('yt_dlp/version.py').read(), 'yt_dlp/version.py', 'exec'))
    return locals()['__version__']


def version_to_list(version):
    version_list = version.split('.')
    return list(map(int, version_list)) + [0] * (4 - len(version_list))


def dependancy_options():
    dependancies = [pycryptodome_module(), 'mutagen'] + collect_submodules('websockets')
    excluded_modules = ['test', 'ytdlp_plugins', 'youtube-dl', 'youtube-dlc']

    yield from (f'--hidden-import={module}' for module in dependancies)
    yield from (f'--exclude-module={module}' for module in excluded_modules)


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


def set_version_info(exe, version):
    if OS_NAME == 'Windows':
        windows_set_version(exe, version)


def windows_set_version(exe, version):
    version_list = version_to_list(version)
    suffix = '_x86' if ARCH == '32' else ''
    SetVersion(exe, VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=version_list,
            prodvers=version_list,
            mask=0x3F,
            flags=0x0,
            OS=0x4,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([StringTable('040904B0', [
                StringStruct('Comments', 'yt-dlp%s Command Line Interface.' % suffix),
                StringStruct('CompanyName', 'https://github.com/yt-dlp'),
                StringStruct('FileDescription', 'yt-dlp%s' % (' (32 Bit)' if ARCH == '32' else '')),
                StringStruct('FileVersion', version),
                StringStruct('InternalName', f'yt-dlp{suffix}'),
                StringStruct('LegalCopyright', 'pukkandan.ytdlp@gmail.com | UNLICENSE'),
                StringStruct('OriginalFilename', f'yt-dlp{suffix}.exe'),
                StringStruct('ProductName', f'yt-dlp{suffix}'),
                StringStruct(
                    'ProductVersion', f'{version}{suffix} on Python {platform.python_version()}'),
            ])]), VarFileInfo([VarStruct('Translation', [0, 1200])])
        ]
    ))


if __name__ == '__main__':
    main()
