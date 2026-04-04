#!/usr/bin/env python3
from __future__ import annotations

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import contextlib
import dataclasses
import datetime as dt
import itertools
import json
import pathlib
import re
import urllib.request

from devscripts.utils import run_process


REQUIREMENTS_PATH = pathlib.Path(__file__).parent.parent / 'bundle/requirements'
INPUT_TMPL = 'requirements-{}.in'
OUTPUT_TMPL = 'requirements-{}.txt'
CUSTOM_COMPILE_COMMAND = 'python -m devscripts.update_bundle_requirements'
COOLDOWN_DATE = (dt.date.today() - dt.timedelta(days=7)).isoformat()
FUTURE_DATE = (dt.date.today() + dt.timedelta(days=1)).isoformat()

COOLDOWN_EXCEPTIONS = ('protobug', 'yt-dlp-ejs')

LINUX_GNU_PYTHON_VERSION = '3.13'
LINUX_MUSL_PYTHON_VERISON = '3.14'
WINDOWS_INTEL_PYTHON_VERSION = '3.10'
WINDOWS_ARM64_PYTHON_VERSION = '3.13'
MACOS_PYTHON_VERSION = '3.14'


@dataclasses.dataclass
class Target:
    platform: str
    version: str
    extras: list[str] = dataclasses.field(default_factory=list)
    groups: list[str] = dataclasses.field(default_factory=list)
    compile_args: list[str] = dataclasses.field(default_factory=list)


INSTALL_DEPS_TARGETS = {
    'linux-x86_64': Target(
        platform='x86_64-manylinux2014',
        version=LINUX_GNU_PYTHON_VERSION,
        extras=['default', 'curl-cffi', 'secretstorage'],
        groups=['pyinstaller'],
    ),
    'linux-aarch64': Target(
        platform='aarch64-manylinux2014',
        version=LINUX_GNU_PYTHON_VERSION,
        extras=['default', 'curl-cffi', 'secretstorage'],
        groups=['pyinstaller'],
    ),
    'linux-armv7l': Target(
        platform='linux',
        version=LINUX_GNU_PYTHON_VERSION,
        extras=['default', 'curl-cffi', 'secretstorage'],
        groups=['pyinstaller'],
    ),
    'musllinux-x86_64': Target(
        platform='x86_64-unknown-linux-musl',
        version=LINUX_MUSL_PYTHON_VERISON,
        extras=['default', 'curl-cffi', 'secretstorage'],
        groups=['pyinstaller'],
    ),
    'musllinux-aarch64': Target(
        platform='aarch64-unknown-linux-musl',
        version=LINUX_MUSL_PYTHON_VERISON,
        extras=['default', 'secretstorage'],
        groups=['pyinstaller', 'curl-cffi'],
    ),
    'win-x64': Target(
        platform='x86_64-pc-windows-msvc',
        version=WINDOWS_INTEL_PYTHON_VERSION,
        extras=['default', 'curl-cffi'],
    ),
    'win-x86': Target(
        platform='i686-pc-windows-msvc',
        version=WINDOWS_INTEL_PYTHON_VERSION,
        extras=['default'],
    ),
    'win-arm64': Target(
        platform='aarch64-pc-windows-msvc',
        version=WINDOWS_ARM64_PYTHON_VERSION,
        extras=['default', 'curl-cffi'],
    ),
    'macos': Target(
        platform='macos',
        version=MACOS_PYTHON_VERSION,
        extras=['default', 'curl-cffi'],
        # NB: Resolve delocate and PyInstaller together since they share dependencies
        groups=['delocate', 'pyinstaller'],
        # curl-cffi and cffi don't provide universal2 wheels, so only directly install their deps
        # NB: uv's --no-emit-package option is equivalent to pip-compile's --unsafe-package option
        compile_args=['--no-emit-package', 'curl-cffi', '--no-emit-package', 'cffi'],
    ),
    # We fuse our own universal2 wheels for curl-cffi+cffi, so we need a separate requirements file
    'macos-curl_cffi': Target(
        platform='macos',
        version=MACOS_PYTHON_VERSION,
        extras=['curl-cffi'],
        # Only need curl-cffi+cffi in this requirements file; their deps are installed directly
        compile_args=[
            # XXX: Try to keep this in sync with curl-cffi's and cffi's transitive dependencies
            f'--no-emit-package={package}' for package in (
                'certifi',
                'markdown-it-py',
                'mdurl',
                'pycparser',
                'pygments',
                'rich',
            )
        ],
    ),
}


@dataclasses.dataclass
class PyInstallerTarget:
    platform: str
    version: str
    asset_tag: str


PYINSTALLER_BUILDS_TARGETS = {
    'win-x64-pyinstaller': PyInstallerTarget(
        platform='x86_64-pc-windows-msvc',
        version=WINDOWS_INTEL_PYTHON_VERSION,
        asset_tag='win_amd64',
    ),
    'win-x86-pyinstaller': PyInstallerTarget(
        platform='i686-pc-windows-msvc',
        version=WINDOWS_INTEL_PYTHON_VERSION,
        asset_tag='win32',
    ),
    'win-arm64-pyinstaller': PyInstallerTarget(
        platform='aarch64-pc-windows-msvc',
        version=WINDOWS_ARM64_PYTHON_VERSION,
        asset_tag='win_arm64',
    ),
}

PYINSTALLER_BUILDS_URL = 'https://api.github.com/repos/yt-dlp/Pyinstaller-Builds/releases/latest'

PYINSTALLER_BUILDS_TMPL = '''\
{}pyinstaller@{} \\
    --hash={}
'''

PYINSTALLER_VERSION_RE = re.compile(r'pyinstaller-(?P<version>[0-9]+\.[0-9]+\.[0-9]+)-')


def write_requirements_input(filepath: pathlib.Path, *args: str) -> None:
    filepath.write_text(run_process(
        sys.executable, '-m', 'devscripts.install_deps',
        '--omit-default', '--print', *args).stdout)


def run_pip_compile(python_platform: str, python_version: str, requirements_input_path: pathlib.Path, *args: str) -> str:
    return run_process(
        'uv', 'pip', 'compile',
        '--no-config',
        '--quiet',
        '--no-progress',
        '--color=never',
        '--upgrade',
        f'--exclude-newer={COOLDOWN_DATE}',
        *(f'--exclude-newer-package={package}={FUTURE_DATE}' for package in COOLDOWN_EXCEPTIONS),
        f'--python-platform={python_platform}',
        f'--python-version={python_version}',
        '--generate-hashes',
        '--no-strip-markers',
        f'--custom-compile-command={CUSTOM_COMPILE_COMMAND}',
        str(requirements_input_path),
        '--format=requirements.txt',
        *args)


def main():
    with contextlib.closing(urllib.request.urlopen(PYINSTALLER_BUILDS_URL)) as resp:
        info = json.load(resp)

    for target_suffix, target in PYINSTALLER_BUILDS_TARGETS.items():
        asset_info = next(asset for asset in info['assets'] if target.asset_tag in asset['name'])
        pyinstaller_version = PYINSTALLER_VERSION_RE.match(asset_info['name']).group('version')
        base_requirements_path = REQUIREMENTS_PATH / INPUT_TMPL.format(target_suffix)
        base_requirements_path.write_text(f'pyinstaller=={pyinstaller_version}\n')
        pyinstaller_builds_deps = run_pip_compile(
            target.platform, target.version, base_requirements_path,
            '--no-emit-package=pyinstaller').stdout
        requirements_path = REQUIREMENTS_PATH / OUTPUT_TMPL.format(target_suffix)
        requirements_path.write_text(PYINSTALLER_BUILDS_TMPL.format(
            pyinstaller_builds_deps, asset_info['browser_download_url'], asset_info['digest']))

    for target_suffix, target in INSTALL_DEPS_TARGETS.items():
        requirements_input_path = REQUIREMENTS_PATH / INPUT_TMPL.format(target_suffix)
        write_requirements_input(
            requirements_input_path,
            *itertools.chain.from_iterable(itertools.product(['--include-extra'], target.extras)),
            *itertools.chain.from_iterable(itertools.product(['--include-group'], target.groups)))
        run_pip_compile(
            target.platform, target.version, requirements_input_path, *target.compile_args,
            f'--output-file={REQUIREMENTS_PATH / OUTPUT_TMPL.format(target_suffix)}')

    pypi_input_path = REQUIREMENTS_PATH / INPUT_TMPL.format('pypi-build')
    write_requirements_input(pypi_input_path, '--include-group', 'build')
    run_pip_compile(
        'linux', LINUX_GNU_PYTHON_VERSION, pypi_input_path,
        f'--output-file={REQUIREMENTS_PATH / OUTPUT_TMPL.format("pypi-build")}')

    pip_input_path = REQUIREMENTS_PATH / INPUT_TMPL.format('pip')
    write_requirements_input(pip_input_path, '--include-group', 'build', '--cherry-pick', 'pip')
    run_pip_compile(
        'windows', WINDOWS_INTEL_PYTHON_VERSION, pip_input_path,
        f'--output-file={REQUIREMENTS_PATH / OUTPUT_TMPL.format("pip")}')


if __name__ == '__main__':
    main()
