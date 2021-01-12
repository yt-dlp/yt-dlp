from __future__ import unicode_literals
from PyInstaller.utils.win32.versioninfo import (
    VarStruct, VarFileInfo, StringStruct, StringTable,
    StringFileInfo, FixedFileInfo, VSVersionInfo, SetVersion,
)
import PyInstaller.__main__

from datetime import datetime

FILE_DESCRIPTION = 'Media Downloader'

exec(compile(open('youtube_dlc/version.py').read(), 'youtube_dlc/version.py', 'exec'))

_LATEST_VERSION = locals()['__version__']

_OLD_VERSION = _LATEST_VERSION.rsplit("-", 1)

if len(_OLD_VERSION) > 0:
    old_ver = _OLD_VERSION[0]

old_rev = ''
if len(_OLD_VERSION) > 1:
    old_rev = _OLD_VERSION[1]

now = datetime.now()
# ver = f'{datetime.today():%Y.%m.%d}'
ver = now.strftime("%Y.%m.%d")
rev = ''

if old_ver == ver:
    if old_rev:
        rev = int(old_rev) + 1
    else:
        rev = 1

_SEPARATOR = '-'

version = _SEPARATOR.join(filter(None, [ver, str(rev)]))

print(version)

version_list = ver.split(".")
_year, _month, _day = [int(value) for value in version_list]
_rev = 0
if rev:
    _rev = rev
_ver_tuple = _year, _month, _day, _rev

version_file = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=_ver_tuple,
        prodvers=_ver_tuple,
        mask=0x3F,
        flags=0x0,
        OS=0x4,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("Comments", "Youtube-dlc Command Line Interface."),
                        StringStruct("CompanyName", "theidel@uni-bremen.de"),
                        StringStruct("FileDescription", FILE_DESCRIPTION),
                        StringStruct("FileVersion", version),
                        StringStruct("InternalName", "youtube-dlc"),
                        StringStruct(
                            "LegalCopyright",
                            "theidel@uni-bremen.de | UNLICENSE",
                        ),
                        StringStruct("OriginalFilename", "youtube-dlc.exe"),
                        StringStruct("ProductName", "Youtube-dlc"),
                        StringStruct("ProductVersion", version + " | git.io/JLh7K"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0, 1200])])
    ]
)

PyInstaller.__main__.run([
    '--name=youtube-dlc',
    '--onefile',
    '--icon=win/icon/cloud.ico',
    'youtube_dlc/__main__.py',
])
SetVersion('dist/youtube-dlc.exe', version_file)
