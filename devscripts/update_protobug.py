#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import hashlib
import pathlib
import urllib.request
import zipfile


PREFIX = '    "protobug=='
BASE_PATH = pathlib.Path(__file__).parent.parent
PYPROJECT_PATH = BASE_PATH / 'pyproject.toml'
RELEASE_URL = 'https://api.github.com/repos/yt-dlp/protobug/releases/latest'
ASSETS = {}
MAKEFILE_PATH = BASE_PATH / 'Makefile'


def request(url: str):
    return contextlib.closing(urllib.request.urlopen(url))


def makefile_variables(
        version: str | None = None,
        name: str | None = None,
        digest: str | None = None,
        data: bytes | None = None,
        keys_only: bool = False,
) -> dict[str, str | None]:
    assert keys_only or all(arg is not None for arg in (version, name, digest, data))

    return {
        'PROTOBUG_VERSION': None if keys_only else version,
        'PROTOBUG_WHEEL_NAME': None if keys_only else name,
        'PROTOBUG_WHEEL_HASH': None if keys_only else digest,
        'PROTOBUG_PY_FOLDERS': None if keys_only else list_wheel_contents(data, 'py', files=False),
        'PROTOBUG_PY_FILES': None if keys_only else list_wheel_contents(data, 'py', folders=False, excludes=['protobug/__main__.py']),
    }


def list_wheel_contents(
        wheel_data: bytes,
        suffix: str | None = None,
        folders: bool = True,
        files: bool = True,
        excludes: list = [],
) -> str:
    assert folders or files, 'at least one of "folders" or "files" must be True'

    with zipfile.ZipFile(io.BytesIO(wheel_data)) as zipf:
        path_gen = (zinfo.filename for zinfo in zipf.infolist())

    filtered = filter(lambda path: path.startswith('protobug/') and path not in excludes, path_gen)
    if suffix:
        filtered = filter(lambda path: path.endswith(f'.{suffix}'), filtered)

    files_list = list(filtered)
    if not folders:
        return ' '.join(files_list)

    folders_list = list(dict.fromkeys(path.rpartition('/')[0] for path in files_list))
    if not files:
        return ' '.join(folders_list)

    return ' '.join(folders_list + files_list)


def main():
    current_version = None
    with PYPROJECT_PATH.open() as file:
        for line in file:
            if not line.startswith(PREFIX):
                continue
            current_version, _, _ = line.removeprefix(PREFIX).partition('"')

    if not current_version:
        print('protobug dependency line could not be found')
        return

    makefile_info = makefile_variables(keys_only=True)
    prefixes = tuple(f'{key} = ' for key in makefile_info)
    with MAKEFILE_PATH.open() as file:
        for line in file:
            if not line.startswith(prefixes):
                continue
            key, _, val = line.partition(' = ')
            makefile_info[key] = val.rstrip()

    with request(RELEASE_URL) as resp:
        info = json.load(resp)

    version = info['tag_name']
    if version == current_version:
        print(f'protobug is up to date! ({version})')
        return

    print(f'Updating protobug from {current_version} to {version}')
    wheel_info = {}
    asset = next(a for a in info['assets'] if a['name'].startswith('protobug-') and a['name'].endswith('.whl'))
    with request(asset['browser_download_url']) as resp:
        data = resp.read()

    # verify digest from github
    digest = asset['digest']
    algo, _, expected = digest.partition(':')
    hexdigest = hashlib.new(algo, data).hexdigest()
    assert hexdigest == expected, f'downloaded attest mismatch ({hexdigest!r} != {expected!r})'

    wheel_info = makefile_variables(version, asset['name'], digest, data)

    assert all(wheel_info.get(key) for key in makefile_info), 'wheel info not found in release'

    content = PYPROJECT_PATH.read_text()
    updated = content.replace(PREFIX + current_version, PREFIX + version)
    PYPROJECT_PATH.write_text(updated)

    makefile = MAKEFILE_PATH.read_text()
    for key in wheel_info:
        makefile = makefile.replace(f'{key} = {makefile_info[key]}', f'{key} = {wheel_info[key]}')
    MAKEFILE_PATH.write_text(makefile)


if __name__ == '__main__':
    main()
