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
        '-i', '--include-extra', metavar='EXTRA', action='append',
        help='include an extra/optional-dependencies list (can be used multiple times)')
    parser.add_argument(
        '-c', '--cherry-pick', metavar='DEPENDENCY', action='append',
        help=(
            'only include a specific dependency from the resulting dependency list '
            '(can be used multiple times)'))
    parser.add_argument(
        '-o', '--omit-default', action='store_true',
        help='omit the "default" extra unless it is explicitly included (it is included by default)')
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
    recursive_pattern = re.compile(rf'{project_table["name"]}\[(?P<extra_name>[\w-]+)\]')
    extras = project_table['optional-dependencies']

    excludes = uniq(args.exclude_dependency)
    only_includes = uniq(args.cherry_pick)
    include_extras = uniq(args.include_extra)

    def yield_deps(extra):
        for dep in extra:
            if mobj := recursive_pattern.fullmatch(dep):
                yield from extras.get(mobj.group('extra_name'), ())
            else:
                yield dep

    targets = {}
    if not args.omit_default:
        # legacy: 'dependencies' is empty now
        targets.update(dict.fromkeys(project_table['dependencies']))
        targets.update(dict.fromkeys(yield_deps(extras['default'])))

    for include in filter(None, map(extras.get, include_extras)):
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
