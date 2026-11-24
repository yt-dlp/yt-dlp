from __future__ import annotations

import functools
from collections.abc import MutableMapping

from ..utils import try_call
from ..extractor.common import InfoExtractor

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable, Any


class _LazyStorage:
    def __init__(self, ie, **kwargs):
        self._ie = ie
        self._cache = kwargs

    def __setattr__(self, name, value, /) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._cache[name] = value

    def __getattr__(self, name: str):
        if name in self._cache:
            return self._cache[name]

        resolver = getattr(self._ie, f"_lazy_{name}")
        result = try_call(resolver, args=(self,))
        self._cache[name] = result
        return result

    def __delattr__(self, name: str) -> None:
        if name.startswith("_"):
            super().__delattr__(name)
        elif name in self._cache:
            del self._cache[name]


class _LazyInfoDict(MutableMapping):
    def __init__(self, data: dict, lazy: dict, ie: InfoExtractor, **kwargs):
        self._data = data
        self._lazy = lazy
        self._ie = ie
        self._storage = _LazyStorage(self._ie, **kwargs)

        for key in self._data.keys() & self._lazy.keys():
            del self._lazy[key]

        self._data.update(dict.fromkeys(self._lazy.keys()))

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        if key in self._lazy:
            compute_func = self._lazy[key]

            # updates = try_call(compute_func, args=(self._storage,), expected_type=dict) or {}
            updates = compute_func(self._ie, self._storage)
            self._data.update(updates)
            for field in updates:
                self._lazy.pop(field, None)

            fields = getattr(compute_func, lazy_fields._field_name, None) or ()
            for field in fields:
                self._lazy.pop(field, None)

        return self._data[key]

    def __setitem__(self, key, value):
        if key in self._lazy:
            del self._lazy[key]

        self._data[key] = value

    def __delitem__(self, key):
        if key in self._lazy:
            del self._lazy[key]

        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        if self._lazy:
            lazy = ", ".join(f"{key!r}: ..." for key in self._lazy.keys())
            data = ", ".join(f"{key!r}: {value!r}" for key, value in self._data.items() if key not in self._lazy)
            data = f"{{{data}}}, lazy={{{lazy}}}"
        else:
            data = f"{self._data!r}"
        return f"{type(self).__name__}({data})"


def _default_lazy_extract(self, url):
    return dict(id=self._match_id(url))


def lazy_ie(klass: type[InfoExtractor] | None = None, /):
    if not klass:
        return lazy_ie

    _old_extract = klass._real_extract
    if _old_extract is InfoExtractor._real_extract:
        _old_extract = _default_lazy_extract

    lazy_members = {}
    for name in dir(klass):
        if not name.startswith("_"):
            continue
        func = getattr(klass, name)
        fields = getattr(func, lazy_fields._field_name, None)
        if not isinstance(fields, tuple):
            continue

        for field in fields:
            lazy_members[field] = func

    @functools.wraps(klass._real_extract)
    def _real_extract(self, url):
        result = _old_extract(self, url)
        assert isinstance(result, dict), 'Lazy extractors need to return a dict'
        return _LazyInfoDict(result, lazy_members, self, url=url, **result)

    klass._real_extract = _real_extract
    return klass


def lazy_fields(*fields: str) -> Callable[[Callable[[Any, _LazyStorage], dict[str, Any]]], Callable[[Any, _LazyStorage], dict[str, Any]]]:
    def _lazy_fields(func):
        setattr(func, lazy_fields._field_name, fields)
        return func

    return _lazy_fields


lazy_fields._field_name = "_lazy_fields"

if __name__ == '__main__':
    from yt_dlp import YoutubeDL

    with YoutubeDL() as ydl:
        result = ydl.extract_info("lazy://<URL>", process=False)
        assert result

        for name in "id", "title", "creator", "description":
            print(f"{name:<10} = {result[name]!r}")
