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

    exit_code = subprocess.call(pip_args)

    if exit_code:
        return exit_code

    # if both Requests, and Niquests are there, make sure the original
    # urllib3 is present. Requests support urllib3.future as a replacement to former urllib3.
    # all of this can be safely removed once Requests is in an optional group, then install it after Niquests.
    # see https://niquests.readthedocs.io/en/latest/community/faq.html#what-is-urllib3-future to learn more.
    if ["niquests" in _ or "requests" in _ for _ in targets].count(True) == 2:
        exit_code = subprocess.call(
            [sys.executable, '-m', 'pip', 'uninstall', '-y', 'urllib3', 'urllib3.future']
        )
        if exit_code:
            return exit_code
        exit_code = subprocess.call(
            [sys.executable, '-m', 'pip', 'install', '-U', 'urllib3.future']
        )
        if exit_code:
            return exit_code
        exit_code = subprocess.call(
            [sys.executable, '-m', 'pip', 'install', '-U', 'urllib3']
        )

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
