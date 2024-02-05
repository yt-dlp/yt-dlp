#!/usr/bin/env python3

from __future__ import annotations

import json
import re

WS = r'(?:[\ \t]*)'
STRING_RE = re.compile(r'"(?:\\.|[^\\"\n])*"|\'[^\'\n]*\'')
SINGLE_KEY_RE = re.compile(rf'{STRING_RE.pattern}|[A-Za-z0-9_-]+')
KEY_RE = re.compile(rf'{WS}(?:{SINGLE_KEY_RE.pattern}){WS}(?:\.{WS}(?:{SINGLE_KEY_RE.pattern}){WS})*')
EQUALS_RE = re.compile(rf'={WS}')
WS_RE = re.compile(WS)

_SUBTABLE = rf'(?P<subtable>^\[(?P<is_list>\[)?(?P<path>{KEY_RE.pattern})\]\]?)'
EXPRESSION_RE = re.compile(rf'^(?:{_SUBTABLE}|{KEY_RE.pattern}=)', re.MULTILINE)

LIST_WS_RE = re.compile(rf'{WS}((#[^\n]*)?\n{WS})*')
UNKNOWN_VALUE_RE = re.compile(r'[^,}\] \t\n#]+')


def parse_key(value: str):
    for match in SINGLE_KEY_RE.finditer(value):
        if match[0][0] == '"':
            yield json.loads(match[0])
        elif match[0][0] == '\'':
            yield match[0][1:-1]
        else:
            yield match[0]


def get_target(root: dict, paths: list[str], is_list=False):
    target = root

    for index, key in enumerate(paths, 1):
        use_list = is_list and index == len(paths)
        result = target.get(key)
        if result is None:
            if use_list:
                target[key] = _temp = []
                target = {}
                _temp.append(target)
            else:
                target[key] = target = {}

        elif isinstance(result, list):
            if use_list:
                target = {}
                result.append(target)
            else:
                target = result[-1]

        else:
            target = result

    assert isinstance(target, dict)
    return target


def parse_enclosed(data: str, index: int, end: str, ws_re: re.Pattern):
    index += 1

    match = ws_re.match(data, index)
    assert match
    index = match.end()

    while data[index] != end:
        index = yield True, index

        if match := ws_re.match(data, index):
            index = match.end()

        if data[index] == ',':
            index += 1

        match = ws_re.match(data, index)
        assert match
        index = match.end()

    yield False, index + 1


def parse_value(data: str, index: int):
    if data[index] == '[':
        result = []

        indices = parse_enclosed(data, index, ']', LIST_WS_RE)
        valid, index = next(indices)
        while valid:
            index, value = parse_value(data, index)
            result.append(value)
            valid, index = indices.send(index)

        return index, result

    if data[index] == '{':
        result = {}

        indices = parse_enclosed(data, index, '}', WS_RE)
        valid, index = next(indices)
        while valid:
            valid, index = indices.send(parse_kv_pair(data, index, result))

        return index, result

    if match := STRING_RE.match(data, index):
        return match.end(), json.loads(match[0]) if match[0][0] == '"' else match[0][1:-1]

    # bool, int, float or date. Of these, only bool is used in pyproject.toml, so ignore others
    match = UNKNOWN_VALUE_RE.match(data, index)
    assert match
    if match[0] == 'true':
        value = True
    elif match[0] == 'false':
        value = False
    else:
        value = None

    return match.end(), value


def parse_kv_pair(data: str, index: int, target: dict):
    match = KEY_RE.match(data, index)
    if not match:
        return None

    *keys, key = parse_key(match[0])

    match = EQUALS_RE.match(data, match.end())
    assert match
    index = match.end()

    index, value = parse_value(data, index)
    get_target(target, keys)[key] = value
    return index


def parse_toml(data: str):
    root = {}
    target = root

    index = 0
    while True:
        match = EXPRESSION_RE.search(data, index)
        if not match:
            break

        if match.group('subtable'):
            index = match.end()
            path, is_list = match.group('path', 'is_list')
            target = get_target(root, list(parse_key(path)), bool(is_list))
            continue

        index = parse_kv_pair(data, match.start(), target)
        assert index is not None

    return root


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument('infile', type=Path, help='The TOML file to read as input')
    args = parser.parse_args()

    with args.infile.open('r', encoding='utf-8') as file:
        data = file.read()

    print(json.dumps(parse_toml(data)))


if __name__ == '__main__':
    main()
