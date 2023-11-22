#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import subprocess
import warnings

try:
    from setuptools import Command, find_packages, setup
    setuptools_available = True
except ImportError:
    from distutils.core import Command, setup
    setuptools_available = False

from devscripts.utils import read_file, read_version

VERSION = read_version(varname='_pkg_version')

DESCRIPTION = 'A youtube-dl fork with additional features and patches'

LONG_DESCRIPTION = '\n\n'.join((
    'Official repository: <https://github.com/yt-dlp/yt-dlp>',
    '**PS**: Some links in this document will not work since this is a copy of the README.md from Github',
    read_file('README.md')))

REQUIREMENTS = read_file('requirements.txt').splitlines()


def packages():
    if setuptools_available:
        return find_packages(exclude=('youtube_dl', 'youtube_dlc', 'test', 'ytdlp_plugins', 'devscripts'))

    return [
        'yt_dlp', 'yt_dlp.extractor', 'yt_dlp.downloader', 'yt_dlp.postprocessor', 'yt_dlp.compat',
    ]


def py2exe_params():
    warnings.warn(
        'py2exe builds do not support pycryptodomex and needs VC++14 to run. '
        'It is recommended to run "pyinst.py" to build using pyinstaller instead')

    return {
        'console': [{
            'script': './yt_dlp/__main__.py',
            'dest_base': 'yt-dlp',
            'icon_resources': [(1, 'devscripts/logo.ico')],
        }],
        'version_info': {
            'version': VERSION,
            'description': DESCRIPTION,
            'comments': LONG_DESCRIPTION.split('\n')[0],
            'product_name': 'yt-dlp',
            'product_version': VERSION,
        },
        'options': {
            'bundle_files': 0,
            'compressed': 1,
            'optimize': 2,
            'dist_dir': './dist',
            'excludes': [
                # py2exe cannot import Crypto
                'Crypto',
                'Cryptodome',
                # py2exe appears to confuse this with our socks library.
                # We don't use pysocks and urllib3.contrib.socks would fail to import if tried.
                'urllib3.contrib.socks'
            ],
            'dll_excludes': ['w9xpopen.exe', 'crypt32.dll'],
            # Modules that are only imported dynamically must be added here
            'includes': ['yt_dlp.compat._legacy', 'yt_dlp.compat._deprecated',
                         'yt_dlp.utils._legacy', 'yt_dlp.utils._deprecated'],
        },
        'zipfile': None,
    }


def build_params():
    files_spec = [
        ('share/bash-completion/completions', ['completions/bash/yt-dlp']),
        ('share/zsh/site-functions', ['completions/zsh/_yt-dlp']),
        ('share/fish/vendor_completions.d', ['completions/fish/yt-dlp.fish']),
        ('share/doc/yt_dlp', ['README.txt']),
        ('share/man/man1', ['yt-dlp.1'])
    ]
    data_files = []
    for dirname, files in files_spec:
        resfiles = []
        for fn in files:
            if not os.path.exists(fn):
                warnings.warn(f'Skipping file {fn} since it is not present. Try running " make pypi-files " first')
            else:
                resfiles.append(fn)
        data_files.append((dirname, resfiles))

    params = {'data_files': data_files}

    if setuptools_available:
        params['entry_points'] = {
            'console_scripts': ['yt-dlp = yt_dlp:main'],
            'pyinstaller40': ['hook-dirs = yt_dlp.__pyinstaller:get_hook_dirs'],
        }
    else:
        params['scripts'] = ['yt-dlp']
    return params


class build_lazy_extractors(Command):
    description = 'Build the extractor lazy loading module'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if self.dry_run:
            print('Skipping build of lazy extractors in dry run mode')
            return
        subprocess.run([sys.executable, 'devscripts/make_lazy_extractors.py'])


def main():
    if sys.argv[1:2] == ['py2exe']:
        params = py2exe_params()
        try:
            from py2exe import freeze
        except ImportError:
            import py2exe  # noqa: F401
            warnings.warn('You are using an outdated version of py2exe. Support for this version will be removed in the future')
            params['console'][0].update(params.pop('version_info'))
            params['options'] = {'py2exe': params.pop('options')}
        else:
            return freeze(**params)
    else:
        params = build_params()

    setup(
        name='yt-dlp',  # package name (do not change/remove comment)
        version=VERSION,
        maintainer='pukkandan',
        maintainer_email='pukkandan.ytdlp@gmail.com',
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type='text/markdown',
        url='https://github.com/yt-dlp/yt-dlp',
        packages=packages(),
        install_requires=REQUIREMENTS,
        python_requires='>=3.8',
        project_urls={
            'Documentation': 'https://github.com/yt-dlp/yt-dlp#readme',
            'Source': 'https://github.com/yt-dlp/yt-dlp',
            'Tracker': 'https://github.com/yt-dlp/yt-dlp/issues',
            'Funding': 'https://github.com/yt-dlp/yt-dlp/blob/master/Collaborators.md#collaborators',
        },
        classifiers=[
            'Topic :: Multimedia :: Video',
            'Development Status :: 5 - Production/Stable',
            'Environment :: Console',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: Implementation',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'License :: Public Domain',
            'Operating System :: OS Independent',
        ],
        cmdclass={'build_lazy_extractors': build_lazy_extractors},
        **params
    )


main()
