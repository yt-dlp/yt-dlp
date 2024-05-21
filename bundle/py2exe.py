#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings

from py2exe import freeze

from devscripts.utils import read_version

VERSION = read_version()


def main():
    warnings.warn(
        'py2exe builds do not support pycryptodomex and needs VC++14 to run. '
        'It is recommended to run "pyinst.py" to build using pyinstaller instead')

    freeze(
        console=[{
            'script': './yt_dlp/__main__.py',
            'dest_base': 'yt-dlp',
            'icon_resources': [(1, 'devscripts/logo.ico')],
        }],
        version_info={
            'version': VERSION,
            'description': 'A feature-rich command-line audio/video downloader',
            'comments': 'Official repository: <https://github.com/yt-dlp/yt-dlp>',
            'product_name': 'yt-dlp',
            'product_version': VERSION,
        },
        options={
            'bundle_files': 0,
            'compressed': 1,
            'optimize': 2,
            'dist_dir': './dist',
            'excludes': [
                # py2exe cannot import Crypto
                'Crypto',
                'Cryptodome',
                # py2exe builds fail to run with requests >=2.32.0
                'requests',
                'urllib3'
            ],
            'dll_excludes': ['w9xpopen.exe', 'crypt32.dll'],
            # Modules that are only imported dynamically must be added here
            'includes': ['yt_dlp.compat._legacy', 'yt_dlp.compat._deprecated',
                         'yt_dlp.utils._legacy', 'yt_dlp.utils._deprecated'],
        },
        zipfile=None,
    )


if __name__ == '__main__':
    main()
