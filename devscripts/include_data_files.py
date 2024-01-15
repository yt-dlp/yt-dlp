#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from devscripts.utils import get_filename_args, read_file

TABLE_HEADER = '[tool.setuptools.data-files]'

FILES_SPEC = {
    'share/bash-completion/completions': ['completions/bash/yt-dlp'],
    'share/zsh/site-functions': ['completions/zsh/_yt-dlp'],
    'share/fish/vendor_completions.d': ['completions/fish/yt-dlp.fish'],
    'share/doc/yt_dlp': ['README.txt'],
    'share/man/man1': ['yt-dlp.1'],
}


def build_data_files(input_file):
    project_root = Path(input_file).resolve().parent

    for dirname, files in FILES_SPEC.items():
        resfiles = [fn for fn in files if (project_root / fn).is_file()]
        if resfiles:
            yield f'"{dirname}" = {resfiles!r}\n'


def main():
    tomlfile = get_filename_args(default_outfile='pyproject.toml')

    if TABLE_HEADER in read_file(tomlfile):
        print(
            f'{tomlfile!r} already contains a data-files table. '
            + 'Try running "make clean-pyproject" or "git restore pyproject.toml"',
            file=sys.stderr)
        return 1

    data_files = list(build_data_files(tomlfile))
    if not data_files:
        print('No data files to include. Try running "make pypi-files"', file=sys.stderr)
        return  # `make` should not error here

    with open(tomlfile, 'a', encoding='utf-8') as f:
        f.write(f'\n{TABLE_HEADER}\n')
        f.writelines(data_files)


if __name__ == '__main__':
    sys.exit(main())
