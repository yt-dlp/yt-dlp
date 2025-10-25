#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import re
import subprocess

from pathlib import Path

from devscripts.tomlparse import parse_toml
from devscripts.utils import read_file


def parse_args():
    parser = argparse.ArgumentParser(description='Install dependencies for yt-dlp')
    parser.add_argument(
        'input', nargs='?', metavar='TOMLFILE', default=Path(__file__).parent.parent / 'pyproject.toml',
        help='input file (default: %(default)s)')
    parser.add_argument(
        '-e', '--exclude-dependency', metavar='DEPENDENCY', action='append',
        help='exclude a dependency (can be used multiple times)')
    parser.add_argument(
        '-i', '--include-group', metavar='GROUP', action='append',
        help='include an optional dependency group (can be used multiple times)')
    parser.add_argument(
        '-d', '--only-include-dependency', metavar='DEPENDENCY', action='append',
        help=(
            'only include a specific dependency from the default dependencies '
            'or a group specified with --include-group (can be used multiple times)'))
    parser.add_argument(
        '-o', '--only-optional-groups', action='store_true',
        help='omit default dependencies unless the "default" group is specified with --include-group')
    parser.add_argument(
        '-p', '--print', action='store_true',
        help='only print requirements to stdout')
    parser.add_argument(
        '-u', '--user', action='store_true',
        help='install with pip as --user')
    return parser.parse_args()


def main():
    args = parse_args()
    project_table = parse_toml(read_file(args.input))['project']
    recursive_pattern = re.compile(rf'{project_table["name"]}\[(?P<group_name>[\w-]+)\]')
    optional_groups = project_table['optional-dependencies']
    excludes = list(map(str.lower, args.exclude_dependency or []))
    only_includes = list(map(str.lower, args.only_include_dependency or []))

    def yield_deps(group):
        for dep in group:
            if mobj := recursive_pattern.fullmatch(dep):
                yield from optional_groups.get(mobj.group('group_name'), [])
            else:
                yield dep

    include_groups = list(dict.fromkeys(map(str.lower, args.include_group or [])))
    targets = []
    if not args.only_optional_groups:
        targets.extend(project_table['dependencies'])  # legacy: 'dependencies' is empty now
        targets.extend(yield_deps(optional_groups['default']))
        # `--include default` shouldn't duplicate the default dependency group
        include_groups = list(filter(lambda group: group != 'default', include_groups))

    for include in filter(None, map(optional_groups.get, include_groups)):
        targets.extend(yield_deps(include))

    def target_filter(target):
        name = re.match(r'[\w-]+', target).group(0).lower()
        return name not in excludes and (not only_includes or name in only_includes)

    targets = list(filter(target_filter, targets))

    if args.print:
        for target in targets:
            print(target)
        return

    pip_args = [sys.executable, '-m', 'pip', 'install', '-U']
    if args.user:
        pip_args.append('--user')
    pip_args.extend(targets)

    return subprocess.call(pip_args)


if __name__ == '__main__':
    sys.exit(main())
