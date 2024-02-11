#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import subprocess

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
