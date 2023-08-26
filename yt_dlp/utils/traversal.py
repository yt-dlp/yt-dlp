import collections.abc
import contextlib
import inspect
import itertools
import re

from ._utils import (
    IDENTITY,
    NO_DEFAULT,
    LazyList,
    int_or_none,
    is_iterable_like,
    try_call,
    variadic,
)


def traverse_obj(
        obj, *paths, default=NO_DEFAULT, expected_type=None, get_all=True,
        casesense=True, is_user_input=False, traverse_string=False):
    """
    Safely traverse nested `dict`s and `Iterable`s

    >>> obj = [{}, {"key": "value"}]
    >>> traverse_obj(obj, (1, "key"))
    "value"

    Each of the provided `paths` is tested and the first producing a valid result will be returned.
    The next path will also be tested if the path branched but no results could be found.
    Supported values for traversal are `Mapping`, `Iterable` and `re.Match`.
    Unhelpful values (`{}`, `None`) are treated as the absence of a value and discarded.

    The paths will be wrapped in `variadic`, so that `'key'` is conveniently the same as `('key', )`.

    The keys in the path can be one of:
        - `None`:           Return the current object.
        - `set`:            Requires the only item in the set to be a type or function,
                            like `{type}`/`{func}`. If a `type`, returns only values
                            of this type. If a function, returns `func(obj)`.
        - `str`/`int`:      Return `obj[key]`. For `re.Match`, return `obj.group(key)`.
        - `slice`:          Branch out and return all values in `obj[key]`.
        - `Ellipsis`:       Branch out and return a list of all values.
        - `tuple`/`list`:   Branch out and return a list of all matching values.
                            Read as: `[traverse_obj(obj, branch) for branch in branches]`.
        - `function`:       Branch out and return values filtered by the function.
                            Read as: `[value for key, value in obj if function(key, value)]`.
                            For `Iterable`s, `key` is the index of the value.
                            For `re.Match`es, `key` is the group number (0 = full match)
                            as well as additionally any group names, if given.
        - `dict`            Transform the current object and return a matching dict.
                            Read as: `{key: traverse_obj(obj, path) for key, path in dct.items()}`.

        `tuple`, `list`, and `dict` all support nested paths and branches.

    @params paths           Paths which to traverse by.
    @param default          Value to return if the paths do not match.
                            If the last key in the path is a `dict`, it will apply to each value inside
                            the dict instead, depth first. Try to avoid if using nested `dict` keys.
    @param expected_type    If a `type`, only accept final values of this type.
                            If any other callable, try to call the function on each result.
                            If the last key in the path is a `dict`, it will apply to each value inside
                            the dict instead, recursively. This does respect branching paths.
    @param get_all          If `False`, return the first matching result, otherwise all matching ones.
    @param casesense        If `False`, consider string dictionary keys as case insensitive.

    The following are only meant to be used by YoutubeDL.prepare_outtmpl and are not part of the API

    @param is_user_input    Whether the keys are generated from user input.
                            If `True` strings get converted to `int`/`slice` if needed.
    @param traverse_string  Whether to traverse into objects as strings.
                            If `True`, any non-compatible object will first be
                            converted into a string and then traversed into.
                            The return value of that path will be a string instead,
                            not respecting any further branching.


    @returns                The result of the object traversal.
                            If successful, `get_all=True`, and the path branches at least once,
                            then a list of results is returned instead.
                            If no `default` is given and the last path branches, a `list` of results
                            is always returned. If a path ends on a `dict` that result will always be a `dict`.
    """
    casefold = lambda k: k.casefold() if isinstance(k, str) else k

    if isinstance(expected_type, type):
        type_test = lambda val: val if isinstance(val, expected_type) else None
    else:
        type_test = lambda val: try_call(expected_type or IDENTITY, args=(val,))

    def apply_key(key, obj, is_last):
        branching = False
        result = None

        if obj is None and traverse_string:
            if key is ... or callable(key) or isinstance(key, slice):
                branching = True
                result = ()

        elif key is None:
            result = obj

        elif isinstance(key, set):
            assert len(key) == 1, 'Set should only be used to wrap a single item'
            item = next(iter(key))
            if isinstance(item, type):
                if isinstance(obj, item):
                    result = obj
            else:
                result = try_call(item, args=(obj,))

        elif isinstance(key, (list, tuple)):
            branching = True
            result = itertools.chain.from_iterable(
                apply_path(obj, branch, is_last)[0] for branch in key)

        elif key is ...:
            branching = True
            if isinstance(obj, collections.abc.Mapping):
                result = obj.values()
            elif is_iterable_like(obj):
                result = obj
            elif isinstance(obj, re.Match):
                result = obj.groups()
            elif traverse_string:
                branching = False
                result = str(obj)
            else:
                result = ()

        elif callable(key):
            branching = True
            if isinstance(obj, collections.abc.Mapping):
                iter_obj = obj.items()
            elif is_iterable_like(obj):
                iter_obj = enumerate(obj)
            elif isinstance(obj, re.Match):
                iter_obj = itertools.chain(
                    enumerate((obj.group(), *obj.groups())),
                    obj.groupdict().items())
            elif traverse_string:
                branching = False
                iter_obj = enumerate(str(obj))
            else:
                iter_obj = ()

            result = (v for k, v in iter_obj if try_call(key, args=(k, v)))
            if not branching:  # string traversal
                result = ''.join(result)

        elif isinstance(key, dict):
            iter_obj = ((k, _traverse_obj(obj, v, False, is_last)) for k, v in key.items())
            result = {
                k: v if v is not None else default for k, v in iter_obj
                if v is not None or default is not NO_DEFAULT
            } or None

        elif isinstance(obj, collections.abc.Mapping):
            result = (try_call(obj.get, args=(key,)) if casesense or try_call(obj.__contains__, args=(key,)) else
                      next((v for k, v in obj.items() if casefold(k) == key), None))

        elif isinstance(obj, re.Match):
            if isinstance(key, int) or casesense:
                with contextlib.suppress(IndexError):
                    result = obj.group(key)

            elif isinstance(key, str):
                result = next((v for k, v in obj.groupdict().items() if casefold(k) == key), None)

        elif isinstance(key, (int, slice)):
            if is_iterable_like(obj, collections.abc.Sequence):
                branching = isinstance(key, slice)
                with contextlib.suppress(IndexError):
                    result = obj[key]
            elif traverse_string:
                with contextlib.suppress(IndexError):
                    result = str(obj)[key]

        return branching, result if branching else (result,)

    def lazy_last(iterable):
        iterator = iter(iterable)
        prev = next(iterator, NO_DEFAULT)
        if prev is NO_DEFAULT:
            return

        for item in iterator:
            yield False, prev
            prev = item

        yield True, prev

    def apply_path(start_obj, path, test_type):
        objs = (start_obj,)
        has_branched = False

        key = None
        for last, key in lazy_last(variadic(path, (str, bytes, dict, set))):
            if is_user_input and isinstance(key, str):
                if key == ':':
                    key = ...
                elif ':' in key:
                    key = slice(*map(int_or_none, key.split(':')))
                elif int_or_none(key) is not None:
                    key = int(key)

            if not casesense and isinstance(key, str):
                key = key.casefold()

            if __debug__ and callable(key):
                # Verify function signature
                inspect.signature(key).bind(None, None)

            new_objs = []
            for obj in objs:
                branching, results = apply_key(key, obj, last)
                has_branched |= branching
                new_objs.append(results)

            objs = itertools.chain.from_iterable(new_objs)

        if test_type and not isinstance(key, (dict, list, tuple)):
            objs = map(type_test, objs)

        return objs, has_branched, isinstance(key, dict)

    def _traverse_obj(obj, path, allow_empty, test_type):
        results, has_branched, is_dict = apply_path(obj, path, test_type)
        results = LazyList(item for item in results if item not in (None, {}))
        if get_all and has_branched:
            if results:
                return results.exhaust()
            if allow_empty:
                return [] if default is NO_DEFAULT else default
            return None

        return results[0] if results else {} if allow_empty and is_dict else None

    for index, path in enumerate(paths, 1):
        result = _traverse_obj(obj, path, index == len(paths), True)
        if result is not None:
            return result

    return None if default is NO_DEFAULT else default


def get_first(obj, *paths, **kwargs):
    return traverse_obj(obj, *((..., *variadic(keys)) for keys in paths), **kwargs, get_all=False)


def dict_get(d, key_or_keys, default=None, skip_false_values=True):
    for val in map(d.get, variadic(key_or_keys)):
        if val is not None and (val or not skip_false_values):
            return val
    return default
