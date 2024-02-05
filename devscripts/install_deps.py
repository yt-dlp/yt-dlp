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
        '-e', '--exclude', metavar='REQUIREMENT', action='append', help='Exclude a required dependency')
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
    toml_data = parse_toml(read_file(args.input))
    deps = toml_data['project']['dependencies']
    targets = deps.copy() if not args.only_optional else []

    for exclude in args.exclude or []:
        for dep in deps:
            simplified_dep = re.match(r'[\w-]+', dep)[0]
            if dep in targets and (exclude.lower() == simplified_dep.lower() or exclude == dep):
                targets.remove(dep)

    optional_deps = toml_data['project']['optional-dependencies']
    for include in args.include or []:
        group = optional_deps.get(include)
        if group:
            targets.extend(group)

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
