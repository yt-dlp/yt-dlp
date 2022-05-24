#!/usr/bin/env python3
import os.path
import sys
import warnings

try:
    from setuptools import Command, find_packages, setup
    setuptools_available = True
except ImportError:
    from distutils.core import Command, setup
    setuptools_available = False
from distutils.spawn import spawn


def read(fname):
    with open(fname, encoding='utf-8') as f:
        return f.read()


# Get the version from yt_dlp/version.py without importing the package
def read_version(fname):
    exec(compile(read(fname), fname, 'exec'))
    return locals()['__version__']


VERSION = read_version('yt_dlp/version.py')

DESCRIPTION = 'A youtube-dl fork with additional features and patches'

LONG_DESCRIPTION = '\n\n'.join((
    'Official repository: <https://github.com/yt-dlp/yt-dlp>',
    '**PS**: Some links in this document will not work since this is a copy of the README.md from Github',
    read('README.md')))

REQUIREMENTS = read('requirements.txt').splitlines()


if sys.argv[1:2] == ['py2exe']:
    import py2exe  # noqa: F401
    warnings.warn(
        'py2exe builds do not support pycryptodomex and needs VC++14 to run. '
        'The recommended way is to use "pyinst.py" to build using pyinstaller')
    params = {
        'console': [{
            'script': './yt_dlp/__main__.py',
            'dest_base': 'yt-dlp',
            'version': VERSION,
            'description': DESCRIPTION,
            'comments': LONG_DESCRIPTION.split('\n')[0],
            'product_name': 'yt-dlp',
            'product_version': VERSION,
        }],
        'options': {
            'py2exe': {
                'bundle_files': 0,
                'compressed': 1,
                'optimize': 2,
                'dist_dir': './dist',
                'excludes': ['Crypto', 'Cryptodome'],  # py2exe cannot import Crypto
                'dll_excludes': ['w9xpopen.exe', 'crypt32.dll'],
                # Modules that are only imported dynamically must be added here
                'includes': ['yt_dlp.compat._legacy'],
            }
        },
        'zipfile': None
    }

else:
    files_spec = [
        ('share/bash-completion/completions', ['completions/bash/yt-dlp']),
        ('share/zsh/site-functions', ['completions/zsh/_yt-dlp']),
        ('share/fish/vendor_completions.d', ['completions/fish/yt-dlp.fish']),
        ('share/doc/yt_dlp', ['README.txt']),
        ('share/man/man1', ['yt-dlp.1'])
    ]
    root = os.path.dirname(os.path.abspath(__file__))
    data_files = []
    for dirname, files in files_spec:
        resfiles = []
        for fn in files:
            if not os.path.exists(fn):
                warnings.warn('Skipping file %s since it is not present. Try running `make pypi-files` first' % fn)
            else:
                resfiles.append(fn)
        data_files.append((dirname, resfiles))

    params = {
        'data_files': data_files,
    }

    if setuptools_available:
        params['entry_points'] = {'console_scripts': ['yt-dlp = yt_dlp:main']}
    else:
        params['scripts'] = ['yt-dlp']


class build_lazy_extractors(Command):
    description = 'Build the extractor lazy loading module'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        spawn([sys.executable, 'devscripts/make_lazy_extractors.py', 'yt_dlp/extractor/lazy_extractors.py'],
              dry_run=self.dry_run)


if setuptools_available:
    packages = find_packages(exclude=('youtube_dl', 'youtube_dlc', 'test', 'ytdlp_plugins'))
else:
    packages = ['yt_dlp', 'yt_dlp.downloader', 'yt_dlp.extractor', 'yt_dlp.postprocessor']


setup(
    name='yt-dlp',
    version=VERSION,
    maintainer='pukkandan',
    maintainer_email='pukkandan.ytdlp@gmail.com',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://github.com/yt-dlp/yt-dlp',
    packages=packages,
    install_requires=REQUIREMENTS,
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'License :: Public Domain',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',

    cmdclass={'build_lazy_extractors': build_lazy_extractors},
    **params
)
