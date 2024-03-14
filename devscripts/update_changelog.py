#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from devscripts.make_changelog import create_changelog, create_parser
from devscripts.utils import read_file, read_version, write_file

# Always run after devscripts/update-version.py, and run before `make doc|pypi-files|tar|all`

if __name__ == '__main__':
    parser = create_parser()
    parser.description = 'Update an existing changelog file with an entry for a new release'
    parser.add_argument(
        '--changelog-path', type=Path, default=Path(__file__).parent.parent / 'Changelog.md',
        help='path to the Changelog file')
    args = parser.parse_args()
    new_entry = create_changelog(args)

    header, sep, changelog = read_file(args.changelog_path).partition('\n### ')
    write_file(args.changelog_path, f'{header}{sep}{read_version()}\n{new_entry}\n{sep}{changelog}')
