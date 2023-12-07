#!/usr/bin/env python3

import argparse
import functools
import os
import re
import subprocess
import sys
from pathlib import Path


IE_TEST_PATTERN = re.compile(r'IE(_all|_\d+)?$')
fix_test_name = functools.partial(IE_TEST_PATTERN.sub, r'\1')


def parse_args():
    parser = argparse.ArgumentParser(description='Run selected yt-dlp tests')
    parser.add_argument(
        'test', help='An extractor test, or one of "core" or "download"', nargs='*')
    parser.add_argument(
        '-k', help='Run a test matching the expression. Same as "pytest -k"', metavar='EXPRESSION')
    return parser.parse_args()


def run_tests(*tests, pattern=None):
    unittest_supported = True
    arguments = []

    for test in tests:
        if test == 'core':
            arguments += ['-m', 'not download']
            unittest_supported = False
        elif test == 'download':
            arguments += ['-m', 'download']
            unittest_supported = False
        else:
            arguments.append(f'test/test_download.py::TestDownload::test_{fix_test_name(test)}')

    if pattern:
        arguments += ['-k', pattern]

    if not arguments:
        arguments = ['-m', 'not download']

    print(f'Running pytest with short traceback on {arguments}')
    try:
        subprocess.run(['pytest', '--tb', 'short'] + arguments)
        return
    except FileNotFoundError:
        pass

    if not unittest_supported:
        print('"pytest" needs to be installed to run the specified tests', file=sys.stderr)
        return

    arguments = [f'test.test_download.TestDownload.test_{fix_test_name(test)}' for test in tests]
    if pattern:
        arguments += ['-k', pattern]

    print(f'Running unittest with {arguments}')
    subprocess.run([sys.executable, '-m', 'unittest'] + arguments)


if __name__ == '__main__':
    args = parse_args()

    os.chdir(Path(__file__).parent.parent)
    run_tests(*args.test, pattern=args.k)
