#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devscripts.make_changelog import create
from devscripts.utils import read_file, read_version, write_file

# Always run after devscripts/update-version.py, and run before `make doc|pypi-files|tar|all`

if __name__ == '__main__':
    header, sep, changelog = read_file('Changelog.md').partition('\n### ')
    write_file('Changelog.md', f'{header}{sep}{read_version()}\n{create()}\n{sep}{changelog}')
