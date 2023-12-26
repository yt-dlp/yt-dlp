#!/usr/bin/env python3

import argparse
import functools
import os
import re
import subprocess
import sys
from pathlib import Path


fix_test_name = functools.partial(re.compile(r'IE(_all|_\d+)?$').sub, r'\1')


def parse_args():
    parser = argparse.ArgumentParser(description='Run selected yt-dlp tests')
    parser.add_argument(
        'test', help='a extractor tests, or one of "core" or "download"', nargs='*')
    parser.add_argument(
        '-k', help='run a test matching EXPRESSION. Same as "pytest -k"', metavar='EXPRESSION')
    return parser.parse_args()


def run_tests(*tests, pattern=None):
    run_core = 'core' in tests or (not pattern and not tests)
    run_download = 'download' in tests
    tests = list(map(fix_test_name, tests))

    arguments = ['pytest', '-Werror', '--tb', 'short']
    if run_core:
        arguments.extend(['-m', 'not download'])
    elif run_download:
        arguments.extend(['-m', 'download'])
    elif pattern:
        arguments.extend(['-k', pattern])
    else:
        arguments.extend(
            f'test/test_download.py::TestDownload::test_{test}' for test in tests)

    print(f'Running {arguments}')
    try:
        subprocess.run(arguments)
        return
    except FileNotFoundError:
        pass

    arguments = [sys.executable, '-Werror', '-m', 'unittest']
    if run_core:
        print('"pytest" needs to be installed to run core tests', file=sys.stderr)
        return
    elif run_download:
        arguments.append('test.test_download')
    elif pattern:
        arguments.extend(['-k', pattern])
    else:
        arguments.extend(
            f'test.test_download.TestDownload.test_{test}' for test in tests)

    print(f'Running {arguments}')
    subprocess.run(arguments)


if __name__ == '__main__':
    try:
        args = parse_args()

        os.chdir(Path(__file__).parent.parent)
        run_tests(*args.test, pattern=args.k)
    except KeyboardInterrupt:
        pass
