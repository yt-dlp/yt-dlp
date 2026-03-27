#!/usr/bin/env python3
from __future__ import annotations

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contextlib
import datetime
import itertools
import json
import pathlib
import re
import urllib.request

from devscripts.utils import run_process


REQUIREMENTS_PATH = pathlib.Path(__file__).parent.parent / 'bundle/requirements'
INPUT_TMPL = 'requirements-{}.in'
OUTPUT_TMPL = 'requirements-{}.txt'
COOLDOWN_DATE = (datetime.datetime.today() - datetime.timedelta(days=5)).strftime('%Y-%m-%d')
CUSTOM_COMPILE_COMMAND = 'python -m devscripts.update_bundle_requirements'

LINUX_GNU_PYTHON_VERSION = '3.13'
LINUX_MUSL_PYTHON_VERISON = '3.14'
WINDOWS_INTEL_PYTHON_VERSION = '3.10'
WINDOWS_ARM64_PYTHON_VERSION = '3.13'
MACOS_PYTHON_VERSION = '3.14'

INSTALL_DEPS_TARGETS = {
    # requirements target suffix: (python platform, python version, [extras], [groups])
    'linux-x86_64': (
        'x86_64-manylinux2014',
        LINUX_GNU_PYTHON_VERSION,
        ['default', 'curl-cffi-compat', 'secretstorage'],
        ['pyinstaller']),
    'linux-aarch64': (
        'aarch64-manylinux2014',
        LINUX_GNU_PYTHON_VERSION,
        ['default', 'curl-cffi-compat', 'secretstorage'],
        ['pyinstaller']),
    'linux-armv7l': (
        'linux',
        LINUX_GNU_PYTHON_VERSION,
        ['default', 'curl-cffi', 'secretstorage'],
        ['pyinstaller']),
    'musllinux-x86_64': (
        'x86_64-unknown-linux-musl',
        LINUX_MUSL_PYTHON_VERISON,
        ['default', 'curl-cffi', 'secretstorage'],
        ['pyinstaller']),
    'musllinux-aarch64': (
        'aarch64-unknown-linux-musl',
        LINUX_MUSL_PYTHON_VERISON,
        ['default', 'secretstorage'],
        ['pyinstaller']),
    'win-x64': (
        'x86_64-pc-windows-msvc',
        WINDOWS_INTEL_PYTHON_VERSION,
        ['default', 'curl-cffi'],
        []),
    'win-x86': (
        'i686-pc-windows-msvc',
        WINDOWS_INTEL_PYTHON_VERSION,
        ['default'],
        []),
    'win-arm64': (
        'aarch64-pc-windows-msvc',
        WINDOWS_ARM64_PYTHON_VERSION,
        ['default', 'curl-cffi'],
        []),
    'macos': (
        'macos',
        MACOS_PYTHON_VERSION,
        ['default'],
        []),
    'macos-curl_cffi': (
        'macos',
        MACOS_PYTHON_VERSION,
        ['curl-cffi-compat'],
        []),
    # Resolve delocate and PyInstaller together since they share dependencies
    'macos-pyinstaller': (
        'macos',
        MACOS_PYTHON_VERSION,
        [],
        ['delocate', 'pyinstaller']),
}

BUILD_GROUP_TARGETS = {
    # requirements target suffix: (python platform, python version)
    'pypi-build': ('linux', LINUX_GNU_PYTHON_VERSION),
    'win-x64-build': ('x86_64-pc-windows-msvc', WINDOWS_INTEL_PYTHON_VERSION),
    'win-x86-build': ('i686-pc-windows-msvc', WINDOWS_INTEL_PYTHON_VERSION),
    'win-arm64-build': ('aarch64-pc-windows-msvc', WINDOWS_ARM64_PYTHON_VERSION),
    'macos-build': ('macos', MACOS_PYTHON_VERSION),
}

PYINSTALLER_BUILDS_TARGETS = {
    # requirements target suffix: (python platform, python version, platform tag)
    'win-x64-pyinstaller': ('x86_64-pc-windows-msvc', WINDOWS_INTEL_PYTHON_VERSION, 'win_amd64'),
    'win-x86-pyinstaller': ('i686-pc-windows-msvc', WINDOWS_INTEL_PYTHON_VERSION, 'win32'),
    'win-arm64-pyinstaller': ('aarch64-pc-windows-msvc', WINDOWS_ARM64_PYTHON_VERSION, 'win_arm64'),
}

PYINSTALLER_BUILDS_URL = 'https://api.github.com/repos/yt-dlp/Pyinstaller-Builds/releases/latest'

PYINSTALLER_BUILDS_TMPL = '''\
{}pyinstaller@{} \\
    --hash={}
'''

PYINSTALLER_VERSION_RE = re.compile(r'pyinstaller-(?P<version>[0-9]+\.[0-9]+\.[0-9]+)-')


def run_pip_compile(python_platform, python_version, requirements_input_path, *args):
    return run_process(
        'uv', 'pip', 'compile',
        '--upgrade',
        f'--exclude-newer={COOLDOWN_DATE}',
        f'--python-platform={python_platform}',
        f'--python-version={python_version}',
        '--generate-hashes',
        '--no-strip-markers',
        f'--custom-compile-command={CUSTOM_COMPILE_COMMAND}',
        str(requirements_input_path),
        *args)


def main():
    with contextlib.closing(urllib.request.urlopen(PYINSTALLER_BUILDS_URL)) as resp:
        info = json.load(resp)

    for target_suffix, target_info in PYINSTALLER_BUILDS_TARGETS.items():
        python_platform, python_version, platform_tag = target_info
        asset_info = next(asset for asset in info['assets'] if platform_tag in asset['name'])
        pyinstaller_version = PYINSTALLER_VERSION_RE.match(asset_info['name']).group('version')
        base_requirements_path = REQUIREMENTS_PATH / INPUT_TMPL.format(target_suffix)
        base_requirements_path.write_text(f'pyinstaller=={pyinstaller_version}\n')
        pyinstaller_builds_deps = run_pip_compile(
            python_platform, python_version, base_requirements_path,
            '--color=never', '--no-emit-package=pyinstaller').stdout
        requirements_path = REQUIREMENTS_PATH / OUTPUT_TMPL.format(target_suffix)
        requirements_path.write_text(PYINSTALLER_BUILDS_TMPL.format(
            pyinstaller_builds_deps, asset_info['browser_download_url'], asset_info['digest']))

    for target_suffix, target_info in INSTALL_DEPS_TARGETS.items():
        python_platform, python_version, extras, groups = target_info
        extras = list(itertools.chain.from_iterable(itertools.product(['--include-extra'], extras)))
        groups = list(itertools.chain.from_iterable(itertools.product(['--include-group'], groups)))
        requirements_input_path = REQUIREMENTS_PATH / INPUT_TMPL.format(target_suffix)
        requirements_input_path.write_text(run_process(
            sys.executable, '-m', 'devscripts.install_deps',
            '--omit-default', '--print', *extras, *groups).stdout)
        run_pip_compile(
            python_platform, python_version, requirements_input_path,
            f'--output-file={REQUIREMENTS_PATH / OUTPUT_TMPL.format(target_suffix)}')

    for target_suffix, target_info in BUILD_GROUP_TARGETS.items():
        python_platform, python_version = target_info
        requirements_input_path = REQUIREMENTS_PATH / INPUT_TMPL.format(target_suffix)
        requirements_input_path.write_text(run_process(
            sys.executable, '-m', 'devscripts.install_deps',
            '--omit-default', '--print', '--include-group', 'build').stdout)
        run_pip_compile(
            python_platform, python_version, requirements_input_path,
            f'--output-file={REQUIREMENTS_PATH / OUTPUT_TMPL.format(target_suffix)}')


if __name__ == '__main__':
    sys.exit(main())
