#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import re
import subprocess

from devscripts.tomlparse import parse_toml
from devscripts.utils import read_file


def parse_args():
    parser = argparse.ArgumentParser(description='Install dependencies for yt-dlp')
    parser.add_argument(
        'input', nargs='?', metavar='TOMLFILE', default='pyproject.toml', help='Input file (default: %(default)s)')
    parser.add_argument(
        '-e', '--exclude', metavar='DEPENDENCY', action='append', help='Exclude a dependency')
    parser.add_argument(
        '-i', '--include', metavar='GROUP', action='append', help='Include an optional dependency group')
    parser.add_argument(
        '-o', '--only-optional', action='store_true', help='Only install optional dependencies')
    parser.add_argument(
        '-p', '--print', action='store_true', help='Only print a requirements.txt to stdout')
    parser.add_argument(
        '-u', '--user', action='store_true', help='Install with pip as --user')
    return parser.parse_args()


def main():
    args = parse_args()
    project_table = parse_toml(read_file(args.input))['project']
    optional_groups = project_table['optional-dependencies']
    excludes = args.exclude or []

    deps = []
    if not args.only_optional:  # `-o` should exclude 'dependencies' and the 'default' group
        deps.extend(project_table['dependencies'])
        if 'default' not in excludes:  # `--exclude default` should exclude entire 'default' group
            deps.extend(optional_groups['default'])

    def name(dependency):
        return re.match(r'[\w-]+', dependency)[0].lower()

    target_map = {name(dep): dep for dep in deps}

    for include in filter(None, map(optional_groups.get, args.include or [])):
        target_map.update(zip(map(name, include), include))

    for exclude in map(name, excludes):
        target_map.pop(exclude, None)

    targets = list(target_map.values())

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
