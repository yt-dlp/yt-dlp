import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


IE_TEST_PATTERN = re.compile(r'IE(_all|_\d+)?$')


def parse_args():
    parser = argparse.ArgumentParser(description='Run selected yt-dlp tests')
    parser.add_argument(
        'test', help='An extractor test, or one of "core" or "download"', nargs='*')
    parser.add_argument(
        '-k', help='Run a test matching the expression. Same as "pytest -k"', metavar='EXPRESSION')
    return parser.parse_args()


def run_tests(*tests, pattern=None):
    command = ['pytest', '--tb', 'short']

    if pattern:
        command.extend(['-k', pattern])

    for test in tests:
        if test == 'core':
            command.extend(['-m', 'not download'])
        elif test == 'download':
            command.extend(['-m', 'download'])
        else:
            test = IE_TEST_PATTERN.sub(r'\1', test)
            command.append(f'test/test_download.py::TestDownload::test_{test}')

    if not command:
        command.extend(['-m', 'not download'])

    print(f'Running {command}')
    os.chdir(Path(__file__).parent.parent)
    try:
        subprocess.run(command)
    except FileNotFoundError:
        print('"pytest" needs to be installed to run the tests', file=sys.stderr)


if __name__ == '__main__':
    args = parse_args()
    run_tests(*args.test, pattern=args.k)
