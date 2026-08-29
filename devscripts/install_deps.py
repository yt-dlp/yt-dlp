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
        '-i', '--include', '--include-extra', '--include-group', metavar='EXTRA/GROUP', action='append', dest='includes',
        help='include an extra/group (can be used multiple times)')
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
    toml_data = parse_toml(read_file(args.input))
    project_table = toml_data['project']
    recursive_pattern = re.compile(rf'{project_table["name"]}\[(?P<extra_name>[\w-]+)\]')
    extras = project_table['optional-dependencies']
    groups = toml_data['dependency-groups']

    excludes = uniq(args.exclude_dependency)
    only_includes = uniq(args.cherry_pick)
    includes = uniq(args.includes)

    def yield_deps_from_extra(extra):
        for dep in extra:
            if mobj := recursive_pattern.fullmatch(dep):
                yield from extras.get(mobj.group('extra_name'), ())
            else:
                yield dep

    def yield_deps_from_group(group):
        for dep in group:
            if isinstance(dep, dict):
                yield from yield_deps_from_group(groups[dep['include-group']])
            else:
                yield dep

    targets = {}
    if not args.omit_default:
        # legacy: 'dependencies' is empty now
        targets.update(dict.fromkeys(project_table['dependencies']))
        targets.update(dict.fromkeys(yield_deps_from_extra(extras['default'])))

    for include in filter(None, map(extras.get, includes)):
        targets.update(dict.fromkeys(yield_deps_from_extra(include)))

    for include in filter(None, map(groups.get, includes)):
        targets.update(dict.fromkeys(yield_deps_from_group(include)))

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
