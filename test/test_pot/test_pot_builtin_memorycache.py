import threading
import time
from collections import OrderedDict
import pytest
from yt_dlp.extractor.youtube.pot._provider import IEContentProvider, BuiltinIEContentProvider
from yt_dlp.utils import bug_reports_message
from yt_dlp.extractor.youtube.pot._builtin.memory_cache import MemoryLRUPCP, memorylru_preference, initialize_global_cache
from yt_dlp.version import __version__
from yt_dlp.extractor.youtube.pot._registry import _pot_cache_providers, _pot_memory_cache


class TestMemoryLRUPCS:

    def test_base_type(self):
        assert issubclass(MemoryLRUPCP, IEContentProvider)
        assert issubclass(MemoryLRUPCP, BuiltinIEContentProvider)

    @pytest.fixture
    def pcp(self, ie, logger) -> MemoryLRUPCP:
        return MemoryLRUPCP(ie, logger, {}, initialize_cache=lambda max_size: (OrderedDict(), threading.Lock(), max_size))

    def test_is_registered(self):
        assert _pot_cache_providers.value.get('MemoryLRU') == MemoryLRUPCP

    def test_initialization(self, pcp):
        assert pcp.PROVIDER_NAME == 'memory'
        assert pcp.PROVIDER_VERSION == __version__
        assert pcp.BUG_REPORT_MESSAGE == bug_reports_message(before='')
        assert pcp.is_available()

    def test_store_and_get(self, pcp):
        pcp.store('key1', 'value1', int(time.time()) + 60)
        assert pcp.get('key1') == 'value1'
        assert len(pcp.cache) == 1

    def test_store_ignore_expired(self, pcp):
        pcp.store('key1', 'value1', int(time.time()) - 1)
        assert len(pcp.cache) == 0
        assert pcp.get('key1') is None
        assert len(pcp.cache) == 0

    def test_store_override_existing_key(self, ie, logger):
        MAX_SIZE = 2
        pcp = MemoryLRUPCP(ie, logger, {}, initialize_cache=lambda max_size: (OrderedDict(), threading.Lock(), MAX_SIZE))
        pcp.store('key1', 'value1', int(time.time()) + 60)
        pcp.store('key2', 'value2', int(time.time()) + 60)
        assert len(pcp.cache) == 2
        pcp.store('key1', 'value2', int(time.time()) + 60)
        # Ensure that the override key gets added to the end of the cache instead of in the same position
        pcp.store('key3', 'value3', int(time.time()) + 60)
        assert pcp.get('key1') == 'value2'

    def test_store_ignore_expired_existing_key(self, pcp):
        pcp.store('key1', 'value2', int(time.time()) + 60)
        pcp.store('key1', 'value1', int(time.time()) - 1)
        assert len(pcp.cache) == 1
        assert pcp.get('key1') == 'value2'
        assert len(pcp.cache) == 1

    def test_get_key_expired(self, pcp):
        pcp.store('key1', 'value1', int(time.time()) + 60)
        assert pcp.get('key1') == 'value1'
        assert len(pcp.cache) == 1
        pcp.cache['key1'] = ('value1', int(time.time()) - 1)
        assert pcp.get('key1') is None
        assert len(pcp.cache) == 0

    def test_lru_eviction(self, ie, logger):
        MAX_SIZE = 2
        provider = MemoryLRUPCP(ie, logger, {}, initialize_cache=lambda max_size: (OrderedDict(), threading.Lock(), MAX_SIZE))
        provider.store('key1', 'value1', int(time.time()) + 5)
        provider.store('key2', 'value2', int(time.time()) + 5)
        assert len(provider.cache) == 2

        assert provider.get('key1') == 'value1'

        provider.store('key3', 'value3', int(time.time()) + 5)
        assert len(provider.cache) == 2

        assert provider.get('key2') is None

        provider.store('key4', 'value4', int(time.time()) + 5)
        assert len(provider.cache) == 2

        assert provider.get('key1') is None
        assert provider.get('key3') == 'value3'
        assert provider.get('key4') == 'value4'

    def test_delete(self, pcp):
        pcp.store('key1', 'value1', int(time.time()) + 5)
        assert len(pcp.cache) == 1
        assert pcp.get('key1') == 'value1'
        pcp.delete('key1')
        assert len(pcp.cache) == 0
        assert pcp.get('key1') is None

    def test_use_global_cache_default(self, ie, logger):
        pcp = MemoryLRUPCP(ie, logger, {})
        assert pcp.max_size == _pot_memory_cache.value['max_size'] == 25
        assert pcp.cache is _pot_memory_cache.value['cache']
        assert pcp.lock is _pot_memory_cache.value['lock']

        pcp2 = MemoryLRUPCP(ie, logger, {})
        assert pcp.max_size == pcp2.max_size == _pot_memory_cache.value['max_size'] == 25
        assert pcp.cache is pcp2.cache is _pot_memory_cache.value['cache']
        assert pcp.lock is pcp2.lock is _pot_memory_cache.value['lock']

    def test_fail_max_size_change_global(self, ie, logger):
        pcp = MemoryLRUPCP(ie, logger, {})
        assert pcp.max_size == _pot_memory_cache.value['max_size'] == 25
        with pytest.raises(ValueError, match='Cannot change max_size of initialized global memory cache'):
            initialize_global_cache(50)

        assert pcp.max_size == _pot_memory_cache.value['max_size'] == 25

    def test_memory_lru_preference(self, pcp, ie, pot_request):
        assert memorylru_preference(pcp, pot_request) == 10000
