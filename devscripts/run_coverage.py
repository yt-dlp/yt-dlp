#!/usr/bin/env python3

# Script to run coverage tests for yt-dlp
#
# Usage:
#   python -m devscripts.run_coverage [test_path] [module_path] [additional pytest args]
#
# Examples:
#   python -m devscripts.run_coverage                         # Test everything
#   python -m devscripts.run_coverage test/devscripts         # Test devscripts
#   python -m devscripts.run_coverage test/test_utils.py yt_dlp.utils  # Test specific module
#   python -m devscripts.run_coverage test/test_utils.py "yt_dlp.utils,yt_dlp.YoutubeDL"  # Test multiple modules
#   python -m devscripts.run_coverage test -v                 # With verbosity
#
# Using hatch:
#   hatch run hatch-test:run-cov [args]                       # Same arguments as above
#   hatch test --cover                                        # Run all tests with coverage
#
# Important:
#   - Always run this script from the project root directory
#   - Test paths are relative to the project root
#   - Module paths use Python import syntax (with dots)
#   - Coverage reports are generated in .coverage-reports/

import sys
import subprocess
from pathlib import Path

script_dir = Path(__file__).parent
repo_root = script_dir.parent


def main():
    args = sys.argv[1:]

    if not args:
        # Default to running all tests
        test_path = 'test'
        module_path = 'yt_dlp,devscripts'
    elif len(args) == 1:
        test_path = args[0]
        # Try to guess the module path from the test path
        if test_path.startswith('test/devscripts'):
            module_path = 'devscripts'
        elif test_path.startswith('test/'):
            module_path = 'yt_dlp'
        else:
            module_path = 'yt_dlp,devscripts'
    else:
        test_path = args[0]
        module_path = args[1]

    # Initialize coverage reports directory
    cov_dir = repo_root / '.coverage-reports'
    cov_dir.mkdir(exist_ok=True)
    html_dir = cov_dir / 'html'
    html_dir.mkdir(exist_ok=True)

    # Run pytest with coverage
    cmd = [
        'python', '-m', 'pytest',
        f'--cov={module_path}',
        '--cov-config=.coveragerc',
        '--cov-report=term-missing',
        test_path,
    ]

    if len(args) > 2:
        cmd.extend(args[2:])

    print(f'Running coverage on {test_path} for module(s) {module_path}')
    print(f'Command: {" ".join(cmd)}')

    try:
        result = subprocess.run(cmd, check=True)

        # Generate reports after the test run in parallel
        import concurrent.futures

        def generate_html_report():
            return subprocess.run([
                'python', '-m', 'coverage', 'html',
            ], check=True)

        def generate_xml_report():
            return subprocess.run([
                'python', '-m', 'coverage', 'xml',
            ], check=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            html_future = executor.submit(generate_html_report)
            xml_future = executor.submit(generate_xml_report)
            # Wait for both tasks to complete
            concurrent.futures.wait([html_future, xml_future])

        print(f'\nCoverage reports saved to {cov_dir.as_posix()}')
        print(f'HTML report: open {cov_dir.as_posix()}/html/index.html')
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f'Error running coverage: {e}')
        return e.returncode


if __name__ == '__main__':
    sys.exit(main())
