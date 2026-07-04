from __future__ import annotations

import base64
import datetime as dt
import math
import re
import struct

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
    'Float16Array': 'e',
    'Int32Array': 'i',
    'Uint32Array': 'I',
    'Float32Array': 'f',
    'Float64Array': 'd',
    'BigInt64Array': 'q',
    'BigUint64Array': 'Q',
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
                target[index] = reviver(target[index])
            except Exception as error:
                yield TypeError(f'failed to parse {source} as {name!r}: {error}')
                target[index] = None
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
                type_name = value[0]
                # TODO: implement zips `strict=True`
                if reviver := revivers.get(type_name):
                    if value[1] == source:
                        # XXX: avoid infinite loop
                        yield IndexError(f'{type_name!r} cannot point to itself (index: {source})')
                        continue
                    # inverse order: resolve index, revive value
                    stack.append((target, index, (type_name, value[1], reviver)))
                    stack.append((target, index, value[1]))
                    continue

                elif type_name == 'Date':
                    try:
                        result = dt.datetime.fromtimestamp(parse_iso8601(value[1]), tz=dt.timezone.utc)
                    except Exception:
                        yield ValueError(f'invalid date: {value[1]!r}')
                        result = None

                elif type_name == 'Set':
                    result = [None] * (len(value) - 1)
                    for offset, new_source in enumerate(value[1:]):
                        stack.append((result, offset, new_source))

                elif type_name == 'Map':
                    result = []
                    for key, new_source in zip(*(iter(value[1:]),) * 2, strict=True):
                        pair = [None, None]
                        stack.append((pair, 0, key))
                        stack.append((pair, 1, new_source))
                        result.append(pair)

                elif type_name == 'RegExp':
                    # XXX: use jsinterp to translate regex flags
                    #      currently ignores `value[2]`
                    result = re.compile(value[1])

                elif type_name == 'Object':
                    result = value[1]

                elif type_name == 'BigInt':
                    result = int(value[1])

                elif type_name == 'null':
                    result = {}
                    for key, new_source in zip(*(iter(value[1:]),) * 2, strict=True):
                        stack.append((result, key, new_source))

                elif type_name == 'ArrayBuffer':
                    try:
                        if len(value) < 2 or not isinstance(value[1], str):
                            raise TypeError(f'Invalid ArrayBuffer encoding: {value[1:]!r}')
                        result = base64.b64decode(value[1])
                    except Exception as error:
                        yield ValueError(f'Invalid ArrayBuffer at {source}: {error}')
                        result = None

                elif type_name in _ARRAY_TYPE_LOOKUP or type_name == 'DataView':
                    try:
                        if len(value) < 2:
                            raise TypeError('Missing ArrayBuffer reference')
                        if isinstance(value[1], str):
                            data = base64.b64decode(value[1])
                        else:
                            buffer_index = value[1]
                            if (
                                not isinstance(buffer_index, int)
                                or isinstance(buffer_index, bool)
                                or not 0 <= buffer_index < len(parsed)
                            ):
                                raise IndexError(f'Invalid ArrayBuffer index: {buffer_index!r}')

                            if buffer_index in resolved:
                                data = resolved[buffer_index]
                                if not isinstance(data, bytes):
                                    raise TypeError(f'Invalid ArrayBuffer reference: {buffer_index!r}')
                            else:
                                buffer = parsed[buffer_index]
                                if not (
                                    isinstance(buffer, list)
                                    and len(buffer) >= 2
                                    and buffer[0] == 'ArrayBuffer'
                                    and isinstance(buffer[1], str)
                                ):
                                    raise TypeError(f'Invalid ArrayBuffer reference: {buffer_index!r}')
                                data = resolved[buffer_index] = base64.b64decode(buffer[1])

                        offset = value[2] if len(value) > 2 else 0
                        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
                            raise ValueError(f'Invalid byte offset: {offset!r}')

                        length = value[3] if len(value) > 3 else None
                        if length is not None and (
                            not isinstance(length, int) or isinstance(length, bool) or length < 0
                        ):
                            raise ValueError(f'Invalid length: {length!r}')

                        if type_name == 'DataView':
                            end = len(data) if length is None else offset + length
                            if offset > len(data) or end > len(data):
                                raise ValueError('View exceeds ArrayBuffer length')
                            result = data[offset:end]
                        else:
                            typecode = _ARRAY_TYPE_LOOKUP[type_name]
                            itemsize = struct.calcsize(f'={typecode}')
                            if offset % itemsize:
                                raise ValueError(f'Byte offset {offset} is not aligned to {itemsize}-byte elements')
                            if offset > len(data):
                                raise ValueError('View exceeds ArrayBuffer length')

                            if length is None:
                                view = data[offset:]
                                if len(view) % itemsize:
                                    raise ValueError(f'Byte length is not a multiple of {itemsize}')
                            else:
                                end = offset + length * itemsize
                                if end > len(data):
                                    raise ValueError('View exceeds ArrayBuffer length')
                                view = data[offset:end]

                            result = [item[0] for item in struct.iter_unpack(f'={typecode}', view)]
                    except Exception as error:
                        yield ValueError(f'Invalid {type_name} at {source}: {error}')
                        result = None

                else:
                    yield TypeError(f'Invalid type at {source}: {type_name!r}')
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
