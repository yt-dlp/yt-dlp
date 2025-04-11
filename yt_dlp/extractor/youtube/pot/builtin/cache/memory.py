from __future__ import annotations

import datetime as dt
import typing
from collections import OrderedDict
from threading import Lock

from yt_dlp.extractor.youtube.pot._provider import BuiltInIEContentProvider
from yt_dlp.extractor.youtube.pot.cache import (
    PoTokenCacheProvider,
    register_pcp,
    register_pcp_preference,
)
from yt_dlp.globals import _pot_memory_cache


def initialize_global_cache(max_size: int):
    if _pot_memory_cache.value.get('cache') is None:
        _pot_memory_cache.value['cache'] = OrderedDict()
        _pot_memory_cache.value['lock'] = Lock()
        _pot_memory_cache.value['max_size'] = max_size

    if _pot_memory_cache.value['max_size'] != max_size:
        raise ValueError('Cannot change max_size of initialized global memory cache')

    return _pot_memory_cache.value['cache'], _pot_memory_cache.value['lock'], _pot_memory_cache.value['max_size']


@register_pcp
class MemoryLRUPCP(PoTokenCacheProvider, BuiltInIEContentProvider):
    PROVIDER_NAME = 'memory'
    DEFAULT_CACHE_SIZE = 25

    def __init__(
        self,
        *args,
        initialize_cache: typing.Callable[[int], tuple[OrderedDict, Lock, int]] = initialize_global_cache,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.cache, self.lock, self.max_size = initialize_cache(self.DEFAULT_CACHE_SIZE)

    def is_available(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        with self.lock:
            if key not in self.cache:
                self.logger.trace('cache miss')
                return None
            value, expires_at = self.cache.pop(key)
            if expires_at < int(dt.datetime.now(dt.timezone.utc).timestamp()):
                self.logger.trace(f'cache expired key={key}')
                return None
            self.cache[key] = (value, expires_at)
            self.logger.trace(f'cache hit key={key}')
            return value

    def store(self, key: str, value: str, expires_at: int):
        with self.lock:
            if expires_at < int(dt.datetime.now(dt.timezone.utc).timestamp()):
                self.logger.trace(f'ignoring expired key={key}')
                return
            if key in self.cache:
                self.cache.pop(key)
            self.cache[key] = (value, expires_at)
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
            self.logger.trace(f'storing key={key}')

    def delete(self, key: str):
        with self.lock:
            self.logger.trace(f'deleting key={key}')
            self.cache.pop(key, None)


@register_pcp_preference(MemoryLRUPCP)
def memorylru_preference(*_, **__):
    # Memory LRU Cache SHOULD be the highest priority
    return 10000
