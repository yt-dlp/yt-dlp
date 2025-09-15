from __future__ import annotations

import array
import base64
import datetime as dt
import math
import re

from .._utils import parse_iso8601

TYPE_CHECKING = False
if TYPE_CHECKING:
    import collections.abc
    import typing

    T = typing.TypeVar('T')


_ARRAY_TYPE_LOOKUP = {
    'Int8Array': 'b',
    'Uint8Array': 'B',
    'Uint8ClampedArray': 'B',
    'Int16Array': 'h',
    'Uint16Array': 'H',
    'Int32Array': 'i',
    'Uint32Array': 'I',
    'Float32Array': 'f',
    'Float64Array': 'd',
    'BigInt64Array': 'l',
    'BigUint64Array': 'L',
    'ArrayBuffer': 'B',
}


def parse_iter(parsed: typing.Any, /, *, revivers: dict[str, collections.abc.Callable[[list], typing.Any]] | None = None):
    # based on https://github.com/Rich-Harris/devalue/blob/f3fd2aa93d79f21746555671f955a897335edb1b/src/parse.js
    resolved = {
        -1: None,
        -2: None,
        -3: math.nan,
        -4: math.inf,
        -5: -math.inf,
        -6: -0.0,
    }

    if isinstance(parsed, int) and not isinstance(parsed, bool):
        if parsed not in resolved or parsed == -2:
            raise ValueError('invalid integer input')
        return resolved[parsed]
    elif not isinstance(parsed, list):
        raise ValueError('expected int or list as input')
    elif not parsed:
        raise ValueError('expected a non-empty list as input')

    if revivers is None:
        revivers = {}
    return_value = [None]
    stack: list[tuple] = [(return_value, 0, 0)]

    while stack:
        target, index, source = stack.pop()
        if isinstance(source, tuple):
            name, source, reviver = source
            try:
                resolved[source] = target[index] = reviver(target[index])
            except Exception as error:
                yield TypeError(f'failed to parse {source} as {name!r}: {error}')
                resolved[source] = target[index] = None
            continue

        if source in resolved:
            target[index] = resolved[source]
            continue

        # guard against Python negative indexing
        if source < 0:
            yield IndexError(f'invalid index: {source!r}')
            continue

        try:
            value = parsed[source]
        except IndexError as error:
            yield error
            continue

        if isinstance(value, list):
            if value and isinstance(value[0], str):
                # TODO: implement zips `strict=True`
                if reviver := revivers.get(value[0]):
                    if value[1] == source:
                        # XXX: avoid infinite loop
                        yield IndexError(f'{value[0]!r} cannot point to itself (index: {source})')
                        continue
                    # inverse order: resolve index, revive value
                    stack.append((target, index, (value[0], value[1], reviver)))
                    stack.append((target, index, value[1]))
                    continue

                elif value[0] == 'Date':
                    try:
                        result = dt.datetime.fromtimestamp(parse_iso8601(value[1]), tz=dt.timezone.utc)
                    except Exception:
                        yield ValueError(f'invalid date: {value[1]!r}')
                        result = None

                elif value[0] == 'Set':
                    result = [None] * (len(value) - 1)
                    for offset, new_source in enumerate(value[1:]):
                        stack.append((result, offset, new_source))

                elif value[0] == 'Map':
                    result = []
                    for key, new_source in zip(*(iter(value[1:]),) * 2):
                        pair = [None, None]
                        stack.append((pair, 0, key))
                        stack.append((pair, 1, new_source))
                        result.append(pair)

                elif value[0] == 'RegExp':
                    # XXX: use jsinterp to translate regex flags
                    #      currently ignores `value[2]`
                    result = re.compile(value[1])

                elif value[0] == 'Object':
                    result = value[1]

                elif value[0] == 'BigInt':
                    result = int(value[1])

                elif value[0] == 'null':
                    result = {}
                    for key, new_source in zip(*(iter(value[1:]),) * 2):
                        stack.append((result, key, new_source))

                elif value[0] in _ARRAY_TYPE_LOOKUP:
                    typecode = _ARRAY_TYPE_LOOKUP[value[0]]
                    data = base64.b64decode(value[1])
                    result = array.array(typecode, data).tolist()

                else:
                    yield TypeError(f'invalid type at {source}: {value[0]!r}')
                    result = None
            else:
                result = len(value) * [None]
                for offset, new_source in enumerate(value):
                    stack.append((result, offset, new_source))

        elif isinstance(value, dict):
            result = {}
            for key, new_source in value.items():
                stack.append((result, key, new_source))

        else:
            result = value

        target[index] = resolved[source] = result

    return return_value[0]


def parse(parsed: typing.Any, /, *, revivers: dict[str, collections.abc.Callable[[typing.Any], typing.Any]] | None = None):
    generator = parse_iter(parsed, revivers=revivers)
    while True:
        try:
            raise generator.send(None)
        except StopIteration as error:
            return error.value
