#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devscripts.make_changelog import create
from devscripts.utils import read_file, read_version, write_file

# Always run after devscripts/update-version.py, and run before `make doc|pypi-files|tar|all`

HEADER = '''# Changelog

<!--
# To create a release, dispatch the https://github.com/yt-dlp/yt-dlp/actions/workflows/release.yml workflow on master
-->
'''

OLD_HEADER = HEADER  # set to old header string if changing the header

if __name__ == '__main__':
    changelog = read_file('Changelog.md')[len(OLD_HEADER):]
    write_file('Changelog.md', f'{HEADER}\n### {read_version()}\n{create()}\n{changelog}')
