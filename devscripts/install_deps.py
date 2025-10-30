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
        '-c', '--cherry-pick', metavar='DEPENDENCY', action='append',
        help=(
            'only include a specific dependency from the resulting dependency list '
            '(can be used multiple times)'))
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


def uniq(arg) -> dict[str, None]:
    return dict.fromkeys(map(str.lower, arg or ()))


def main():
    args = parse_args()
    project_table = parse_toml(read_file(args.input))['project']
    recursive_pattern = re.compile(rf'{project_table["name"]}\[(?P<group_name>[\w-]+)\]')
    optional_groups = project_table['optional-dependencies']

    excludes = uniq(args.exclude_dependency)
    only_includes = uniq(args.cherry_pick)
    include_groups = uniq(args.include_group)

    def yield_deps(group):
        for dep in group:
            if mobj := recursive_pattern.fullmatch(dep):
                yield from optional_groups.get(mobj.group('group_name'), ())
            else:
                yield dep

    targets = {}
    if not args.only_optional_groups:
        # legacy: 'dependencies' is empty now
        targets.update(dict.fromkeys(project_table['dependencies']))
        targets.update(dict.fromkeys(yield_deps(optional_groups['default'])))

    for include in filter(None, map(optional_groups.get, include_groups)):
        targets.update(dict.fromkeys(yield_deps(include)))

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
