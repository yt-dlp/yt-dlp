from __future__ import annotations
import abc
import base64
import dataclasses
import hashlib
import json
import time
import pytest

from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider, IEContentProvider

from yt_dlp.extractor.youtube.pot.provider import (
    PoTokenRequest,
    PoTokenContext,
    PoTokenProviderError,
    PoTokenProviderRejectedRequest,
)
from yt_dlp.extractor.youtube.pot._director import (
    PoTokenCache,
    validate_cache_spec,
    clean_pot,
    validate_response,
    PoTokenRequestDirector,
    provider_display_list,
)

from yt_dlp.extractor.youtube.pot.cache import (
    PoTokenCacheSpec,
    PoTokenCacheSpecProvider,
    PoTokenCacheProvider,
    CacheProviderWritePolicy,
    PoTokenCacheProviderError,
)


from yt_dlp.extractor.youtube.pot.provider import (
    PoTokenResponse,
    PoTokenProvider,
)


class BaseMockPoTokenProvider(PoTokenProvider, abc.ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_called_times = 0
        self.request_called_times = 0
        self.close_called = False

    def is_available(self) -> bool:
        self.available_called_times += 1
        return True

    def request_pot(self, *args, **kwargs):
        self.request_called_times += 1
        return super().request_pot(*args, **kwargs)

    def close(self):
        self.close_called = True
        super().close()


class ExamplePTP(BaseMockPoTokenProvider):
    PROVIDER_NAME = 'example'
    PROVIDER_VERSION = '0.0.1'
    BUG_REPORT_LOCATION = 'https://example.com/issues'

    _SUPPORTED_CLIENTS = ('WEB',)
    _SUPPORTED_CONTEXTS = (PoTokenContext.GVS, )

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        if request.data_sync_id == 'example':
            return PoTokenResponse(request.video_id)
        return PoTokenResponse(EXAMPLE_PO_TOKEN)


def success_ptp(response: PoTokenResponse | None = None, key: str | None = None):
    class SuccessPTP(BaseMockPoTokenProvider):
        PROVIDER_NAME = 'success'
        PROVIDER_VERSION = '0.0.1'
        BUG_REPORT_LOCATION = 'https://success.example.com/issues'

        _SUPPORTED_CLIENTS = ('WEB',)
        _SUPPORTED_CONTEXTS = (PoTokenContext.GVS,)

        def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
            return response or PoTokenResponse(EXAMPLE_PO_TOKEN)

    if key:
        SuccessPTP.PROVIDER_KEY = key
    return SuccessPTP


@pytest.fixture
def pot_provider(ie, logger):
    return success_ptp()(ie=ie, logger=logger, settings={})


class UnavailablePTP(BaseMockPoTokenProvider):
    PROVIDER_NAME = 'unavailable'
    BUG_REPORT_LOCATION = 'https://unavailable.example.com/issues'
    _SUPPORTED_CLIENTS = None
    _SUPPORTED_CONTEXTS = None

    def is_available(self) -> bool:
        super().is_available()
        return False

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        raise PoTokenProviderError('something went wrong')


class UnsupportedPTP(BaseMockPoTokenProvider):
    PROVIDER_NAME = 'unsupported'
    BUG_REPORT_LOCATION = 'https://unsupported.example.com/issues'
    _SUPPORTED_CLIENTS = None
    _SUPPORTED_CONTEXTS = None

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        raise PoTokenProviderRejectedRequest('unsupported request')


class ErrorPTP(BaseMockPoTokenProvider):
    PROVIDER_NAME = 'error'
    BUG_REPORT_LOCATION = 'https://error.example.com/issues'
    _SUPPORTED_CLIENTS = None
    _SUPPORTED_CONTEXTS = None

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        expected = request.video_id == 'expected'
        raise PoTokenProviderError('an error occurred', expected=expected)


class UnexpectedErrorPTP(BaseMockPoTokenProvider):
    PROVIDER_NAME = 'unexpected_error'
    BUG_REPORT_LOCATION = 'https://unexpected.example.com/issues'
    _SUPPORTED_CLIENTS = None
    _SUPPORTED_CONTEXTS = None

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        raise ValueError('an unexpected error occurred')


class InvalidPTP(BaseMockPoTokenProvider):
    PROVIDER_NAME = 'invalid'
    BUG_REPORT_LOCATION = 'https://invalid.example.com/issues'
    _SUPPORTED_CLIENTS = None
    _SUPPORTED_CONTEXTS = None

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        if request.video_id == 'invalid_type':
            return 'invalid-response'
        else:
            return PoTokenResponse('example-token?', expires_at='123')


class BaseMockCacheSpecProvider(PoTokenCacheSpecProvider, abc.ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generate_called_times = 0
        self.is_available_called_times = 0
        self.close_called = False

    def is_available(self) -> bool:
        self.is_available_called_times += 1
        return super().is_available()

    def generate_cache_spec(self, request: PoTokenRequest):
        self.generate_called_times += 1

    def close(self):
        self.close_called = True
        super().close()


class ExampleCacheSpecProviderPCSP(BaseMockCacheSpecProvider):

    PROVIDER_NAME = 'example'
    PROVIDER_VERSION = '0.0.1'
    BUG_REPORT_LOCATION = 'https://example.com/issues'

    def generate_cache_spec(self, request: PoTokenRequest):
        super().generate_cache_spec(request)
        return PoTokenCacheSpec(
            key_bindings={'v': request.video_id, 'e': None},
            default_ttl=60,
        )


class UnavailableCacheSpecProviderPCSP(BaseMockCacheSpecProvider):

    PROVIDER_NAME = 'unavailable'
    PROVIDER_VERSION = '0.0.1'

    def is_available(self) -> bool:
        super().is_available()
        return False

    def generate_cache_spec(self, request: PoTokenRequest):
        super().generate_cache_spec(request)
        return None


class UnsupportedCacheSpecProviderPCSP(BaseMockCacheSpecProvider):

    PROVIDER_NAME = 'unsupported'
    PROVIDER_VERSION = '0.0.1'

    def generate_cache_spec(self, request: PoTokenRequest):
        super().generate_cache_spec(request)
        return None


class InvalidSpecCacheSpecProviderPCSP(BaseMockCacheSpecProvider):

    PROVIDER_NAME = 'invalid'
    PROVIDER_VERSION = '0.0.1'

    def generate_cache_spec(self, request: PoTokenRequest):
        super().generate_cache_spec(request)
        return 'invalid-spec'


class ErrorSpecCacheSpecProviderPCSP(BaseMockCacheSpecProvider):

    PROVIDER_NAME = 'invalid'
    PROVIDER_VERSION = '0.0.1'

    def generate_cache_spec(self, request: PoTokenRequest):
        super().generate_cache_spec(request)
        raise ValueError('something went wrong')


class BaseMockCacheProvider(PoTokenCacheProvider, abc.ABC):
    BUG_REPORT_MESSAGE = 'example bug report message'

    def __init__(self, *args, available=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.store_calls = 0
        self.delete_calls = 0
        self.get_calls = 0
        self.available_called_times = 0
        self.available = available

    def is_available(self) -> bool:
        self.available_called_times += 1
        return self.available

    def store(self, *args, **kwargs):
        self.store_calls += 1

    def delete(self, *args, **kwargs):
        self.delete_calls += 1

    def get(self, *args, **kwargs):
        self.get_calls += 1

    def close(self):
        self.close_called = True
        super().close()


class ErrorPCP(BaseMockCacheProvider):
    PROVIDER_NAME = 'error'

    def store(self, *args, **kwargs):
        super().store(*args, **kwargs)
        raise PoTokenCacheProviderError('something went wrong')

    def get(self, *args, **kwargs):
        super().get(*args, **kwargs)
        raise PoTokenCacheProviderError('something went wrong')


class UnexpectedErrorPCP(BaseMockCacheProvider):
    PROVIDER_NAME = 'unexpected_error'

    def store(self, *args, **kwargs):
        super().store(*args, **kwargs)
        raise ValueError('something went wrong')

    def get(self, *args, **kwargs):
        super().get(*args, **kwargs)
        raise ValueError('something went wrong')


class MockMemoryPCP(BaseMockCacheProvider):
    PROVIDER_NAME = 'memory'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}

    def store(self, key, value, expires_at):
        super().store(key, value, expires_at)
        self.cache[key] = (value, expires_at)

    def delete(self, key):
        super().delete(key)
        self.cache.pop(key, None)

    def get(self, key):
        super().get(key)
        return self.cache.get(key, [None])[0]


def create_memory_pcp(ie, logger, provider_key='memory', provider_name='memory', available=True):
    cache = MockMemoryPCP(ie, logger, {}, available=available)
    cache.PROVIDER_KEY = provider_key
    cache.PROVIDER_NAME = provider_name
    return cache


@pytest.fixture
def memorypcp(ie, logger) -> MockMemoryPCP:
    return create_memory_pcp(ie, logger)


@pytest.fixture
def pot_cache(ie, logger):
    class MockPoTokenCache(PoTokenCache):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.get_calls = 0
            self.store_calls = 0
            self.close_called = False

        def get(self, *args, **kwargs):
            self.get_calls += 1
            return super().get(*args, **kwargs)

        def store(self, *args, **kwargs):
            self.store_calls += 1
            return super().store(*args, **kwargs)

        def close(self):
            self.close_called = True
            super().close()

    return MockPoTokenCache(
        cache_providers=[MockMemoryPCP(ie, logger, {})],
        cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie, logger, settings={})],
        logger=logger,
    )


EXAMPLE_PO_TOKEN = base64.urlsafe_b64encode(b'example-token').decode()


class TestPoTokenCache:

    def test_cache_success(self, memorypcp, pot_request, ie, logger):
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        cache.store(pot_request, response)

        cached_response = cache.get(pot_request)
        assert cached_response is not None
        assert cached_response.po_token == EXAMPLE_PO_TOKEN
        assert cached_response.expires_at is not None

        assert cache.get(dataclasses.replace(pot_request, video_id='another-video-id')) is None

    def test_unsupported_cache_spec_no_fallback(self, memorypcp, pot_request, ie, logger):
        unsupported_provider = UnsupportedCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[unsupported_provider],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        assert cache.get(pot_request) is None
        assert unsupported_provider.generate_called_times == 1
        cache.store(pot_request, response)
        assert len(memorypcp.cache) == 0
        assert unsupported_provider.generate_called_times == 2
        assert cache.get(pot_request) is None
        assert unsupported_provider.generate_called_times == 3
        assert len(logger.messages.get('error', [])) == 0

    def test_unsupported_cache_spec_fallback(self, memorypcp, pot_request, ie, logger):
        unsupported_provider = UnsupportedCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        example_provider = ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[unsupported_provider, example_provider],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        assert unsupported_provider.generate_called_times == 1
        assert example_provider.generate_called_times == 1

        cache.store(pot_request, response)
        assert unsupported_provider.generate_called_times == 2
        assert example_provider.generate_called_times == 2

        cached_response = cache.get(pot_request)
        assert unsupported_provider.generate_called_times == 3
        assert example_provider.generate_called_times == 3
        assert cached_response is not None
        assert cached_response.po_token == EXAMPLE_PO_TOKEN
        assert cached_response.expires_at is not None

        assert len(logger.messages.get('error', [])) == 0

    def test_invalid_cache_spec_no_fallback(self, memorypcp, pot_request, ie, logger):
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[InvalidSpecCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        cache.store(pot_request, response)

        assert cache.get(pot_request) is None

        assert 'PoTokenCacheSpecProvider "InvalidSpecCacheSpecProvider" generate_cache_spec() returned invalid spec invalid-spec; please report this issue to the provider developer at  (developer has not provided a bug report location)  .' in logger.messages['error']

    def test_invalid_cache_spec_fallback(self, memorypcp, pot_request, ie, logger):

        invalid_provider = InvalidSpecCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        example_provider = ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[invalid_provider, example_provider],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        assert invalid_provider.generate_called_times == example_provider.generate_called_times == 1

        cache.store(pot_request, response)
        assert invalid_provider.generate_called_times == example_provider.generate_called_times == 2

        cached_response = cache.get(pot_request)
        assert invalid_provider.generate_called_times == example_provider.generate_called_times == 3
        assert cached_response is not None
        assert cached_response.po_token == EXAMPLE_PO_TOKEN
        assert cached_response.expires_at is not None

        assert 'PoTokenCacheSpecProvider "InvalidSpecCacheSpecProvider" generate_cache_spec() returned invalid spec invalid-spec; please report this issue to the provider developer at  (developer has not provided a bug report location)  .' in logger.messages['error']

    def test_unavailable_cache_spec_no_fallback(self, memorypcp, pot_request, ie, logger):
        unavailable_provider = UnavailableCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[unavailable_provider],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        cache.store(pot_request, response)
        assert cache.get(pot_request) is None
        assert unavailable_provider.generate_called_times == 0

    def test_unavailable_cache_spec_fallback(self, memorypcp, pot_request, ie, logger):
        unavailable_provider = UnavailableCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        example_provider = ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[unavailable_provider, example_provider],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        assert unavailable_provider.generate_called_times == 0
        assert unavailable_provider.is_available_called_times == 1
        assert example_provider.generate_called_times == 1

        cache.store(pot_request, response)
        assert unavailable_provider.generate_called_times == 0
        assert unavailable_provider.is_available_called_times == 2
        assert example_provider.generate_called_times == 2

        cached_response = cache.get(pot_request)
        assert unavailable_provider.generate_called_times == 0
        assert unavailable_provider.is_available_called_times == 3
        assert example_provider.generate_called_times == 3
        assert example_provider.is_available_called_times == 3
        assert cached_response is not None
        assert cached_response.po_token == EXAMPLE_PO_TOKEN
        assert cached_response.expires_at is not None

    def test_unexpected_error_cache_spec(self, memorypcp, pot_request, ie, logger):
        error_provider = ErrorSpecCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[error_provider],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        cache.store(pot_request, response)
        assert cache.get(pot_request) is None
        assert error_provider.generate_called_times == 3
        assert error_provider.is_available_called_times == 3

        assert 'Error occurred with "invalid" PO Token cache spec provider: ValueError(\'something went wrong\'); please report this issue to the provider developer at  (developer has not provided a bug report location)  .' in logger.messages['error']

    def test_unexpected_error_cache_spec_fallback(self, memorypcp, pot_request, ie, logger):
        error_provider = ErrorSpecCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        example_provider = ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[error_provider, example_provider],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        assert cache.get(pot_request) is None
        assert error_provider.generate_called_times == 1
        assert error_provider.is_available_called_times == 1
        assert example_provider.generate_called_times == 1

        cache.store(pot_request, response)
        assert error_provider.generate_called_times == 2
        assert error_provider.is_available_called_times == 2
        assert example_provider.generate_called_times == 2

        cached_response = cache.get(pot_request)
        assert error_provider.generate_called_times == 3
        assert error_provider.is_available_called_times == 3
        assert example_provider.generate_called_times == 3
        assert example_provider.is_available_called_times == 3
        assert cached_response is not None
        assert cached_response.po_token == EXAMPLE_PO_TOKEN
        assert cached_response.expires_at is not None

        assert 'Error occurred with "invalid" PO Token cache spec provider: ValueError(\'something went wrong\'); please report this issue to the provider developer at  (developer has not provided a bug report location)  .' in logger.messages['error']

    def test_key_bindings_spec_provider(self, memorypcp, pot_request, ie, logger):

        class ExampleProviderPCSP(PoTokenCacheSpecProvider):
            PROVIDER_NAME = 'example'

            def generate_cache_spec(self, request: PoTokenRequest):
                return PoTokenCacheSpec(
                    key_bindings={'v': request.video_id},
                    default_ttl=60,
                )

        class ExampleProviderTwoPCSP(ExampleProviderPCSP):
            pass

        example_provider = ExampleProviderPCSP(ie=ie, logger=logger, settings={})
        example_provider_two = ExampleProviderTwoPCSP(ie=ie, logger=logger, settings={})

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)

        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[example_provider],
            logger=logger,
        )

        assert cache.get(pot_request) is None
        cache.store(pot_request, response)
        assert len(memorypcp.cache) == 1
        assert hashlib.sha256(
            f"{{'_dlp_cache': 'v1', '_p': 'ExampleProvider', 'v': '{pot_request.video_id}'}}".encode()).hexdigest() in memorypcp.cache

        # The second spec provider returns the exact same key bindings as the first one,
        # however the PoTokenCache should use the provider key to differentiate between them
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[example_provider_two],
            logger=logger,
        )

        assert cache.get(pot_request) is None
        cache.store(pot_request, response)
        assert len(memorypcp.cache) == 2
        assert hashlib.sha256(
            f"{{'_dlp_cache': 'v1', '_p': 'ExampleProviderTwo', 'v': '{pot_request.video_id}'}}".encode()).hexdigest() in memorypcp.cache

    def test_cache_provider_preferences(self, pot_request, ie, logger):
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')
        pcp_two = create_memory_pcp(ie, logger, provider_key='memory_pcp_two')

        cache = PoTokenCache(
            cache_providers=[pcp_one, pcp_two],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN), write_policy=CacheProviderWritePolicy.WRITE_FIRST)
        assert len(pcp_one.cache) == 1
        assert len(pcp_two.cache) == 0

        assert cache.get(pot_request)
        assert pcp_one.get_calls == 1
        assert pcp_two.get_calls == 0

        standard_preference_called = False
        pcp_one_preference_claled = False

        def standard_preference(provider, request, *_, **__):
            nonlocal standard_preference_called
            standard_preference_called = True
            assert isinstance(provider, PoTokenCacheProvider)
            assert isinstance(request, PoTokenRequest)
            return 1

        def pcp_one_preference(provider, request, *_, **__):
            nonlocal pcp_one_preference_claled
            pcp_one_preference_claled = True
            assert isinstance(provider, PoTokenCacheProvider)
            assert isinstance(request, PoTokenRequest)
            if provider.PROVIDER_KEY == pcp_one.PROVIDER_KEY:
                return -100
            return 0

        # test that it can hanldle multiple preferences
        cache.cache_provider_preferences.append(standard_preference)
        cache.cache_provider_preferences.append(pcp_one_preference)

        cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN), write_policy=CacheProviderWritePolicy.WRITE_FIRST)
        assert cache.get(pot_request)
        assert len(pcp_one.cache) == len(pcp_two.cache) == 1
        assert pcp_two.get_calls == pcp_one.get_calls == 1
        assert pcp_one.store_calls == pcp_two.store_calls == 1
        assert standard_preference_called
        assert pcp_one_preference_claled

    def test_secondary_cache_provider_hit(self, pot_request, ie, logger):
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')
        pcp_two = create_memory_pcp(ie, logger, provider_key='memory_pcp_two')

        cache = PoTokenCache(
            cache_providers=[pcp_two],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        # Given the lower priority provider has the cache hit, store the response in the higher priority provider
        cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN))
        assert cache.get(pot_request)

        cache.cache_providers[pcp_one.PROVIDER_KEY] = pcp_one

        def pcp_one_pref(provider, *_, **__):
            if provider.PROVIDER_KEY == pcp_one.PROVIDER_KEY:
                return 1
            return -1

        cache.cache_provider_preferences.append(pcp_one_pref)

        assert cache.get(pot_request)
        assert pcp_one.get_calls == 1
        assert pcp_two.get_calls == 2
        # Should write back to pcp_one (now the highest priority cache provider)
        assert pcp_one.store_calls == pcp_two.store_calls == 1
        assert 'Writing PO Token response to highest priority cache provider' in logger.messages['trace']

    def test_cache_provider_no_hits(self, pot_request, ie, logger):
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')
        pcp_two = create_memory_pcp(ie, logger, provider_key='memory_pcp_two')

        cache = PoTokenCache(
            cache_providers=[pcp_one, pcp_two],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        assert cache.get(pot_request) is None
        assert pcp_one.get_calls == pcp_two.get_calls == 1

    def test_get_invalid_po_token_response(self, pot_request, ie, logger):
        # Test various scenarios where the po token response stored in the cache provider is invalid
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')
        pcp_two = create_memory_pcp(ie, logger, provider_key='memory_pcp_two')

        cache = PoTokenCache(
            cache_providers=[pcp_one, pcp_two],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        valid_response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, valid_response)
        assert len(pcp_one.cache) == len(pcp_two.cache) == 1
        # Overwrite the valid response with an invalid one in the cache
        pcp_one.store(next(iter(pcp_one.cache.keys())), json.dumps(dataclasses.asdict(PoTokenResponse(None))), int(time.time() + 1000))
        assert cache.get(pot_request).po_token == valid_response.po_token
        assert pcp_one.get_calls == pcp_two.get_calls == 1
        assert pcp_one.delete_calls == 1  # Invalid response should be deleted from cache
        assert pcp_one.store_calls == 3  # Since response was fetched from second cache provider, it should be stored in the first one
        assert len(pcp_one.cache) == 1
        assert 'Invalid PO Token response retrieved from cache provider "memory": {"po_token": null, "expires_at": null}; example bug report message' in logger.messages['error']

        # Overwrite the valid response with an invalid json in the cache
        pcp_one.store(next(iter(pcp_one.cache.keys())), 'invalid-json', int(time.time() + 1000))
        assert cache.get(pot_request).po_token == valid_response.po_token
        assert pcp_one.get_calls == pcp_two.get_calls == 2
        assert pcp_one.delete_calls == 2
        assert pcp_one.store_calls == 5  # 3 + 1 store we made in the test + 1 store from lower priority cache provider
        assert len(pcp_one.cache) == 1

        assert 'Invalid PO Token response retrieved from cache provider "memory": invalid-json; example bug report message' in logger.messages['error']

        # Valid json, but missing required fields
        pcp_one.store(next(iter(pcp_one.cache.keys())), '{"unknown_param": 0}', int(time.time() + 1000))
        assert cache.get(pot_request).po_token == valid_response.po_token
        assert pcp_one.get_calls == pcp_two.get_calls == 3
        assert pcp_one.delete_calls == 3
        assert pcp_one.store_calls == 7  # 5 + 1 store from test + 1 store from lower priority cache provider
        assert len(pcp_one.cache) == 1

        assert 'Invalid PO Token response retrieved from cache provider "memory": {"unknown_param": 0}; example bug report message' in logger.messages['error']

    def test_store_invalid_po_token_response(self, pot_request, ie, logger):
        # Should not store an invalid po token response
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')

        cache = PoTokenCache(
            cache_providers=[pcp_one],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        cache.store(pot_request, PoTokenResponse(po_token=EXAMPLE_PO_TOKEN, expires_at=80))
        assert cache.get(pot_request) is None
        assert pcp_one.store_calls == 0
        assert 'Invalid PO Token response provided to PoTokenCache.store()' in logger.messages['error'][0]

    def test_store_write_policy(self, pot_request, ie, logger):
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')
        pcp_two = create_memory_pcp(ie, logger, provider_key='memory_pcp_two')

        cache = PoTokenCache(
            cache_providers=[pcp_one, pcp_two],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN), write_policy=CacheProviderWritePolicy.WRITE_FIRST)
        assert pcp_one.store_calls == 1
        assert pcp_two.store_calls == 0

        cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN), write_policy=CacheProviderWritePolicy.WRITE_ALL)
        assert pcp_one.store_calls == 2
        assert pcp_two.store_calls == 1

    def test_store_write_first_policy_cache_spec(self, pot_request, ie, logger):
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')
        pcp_two = create_memory_pcp(ie, logger, provider_key='memory_pcp_two')

        class WriteFirstPCSP(BaseMockCacheSpecProvider):
            def generate_cache_spec(self, request: PoTokenRequest):
                super().generate_cache_spec(request)
                return PoTokenCacheSpec(
                    key_bindings={'v': request.video_id, 'e': None},
                    default_ttl=60,
                    write_policy=CacheProviderWritePolicy.WRITE_FIRST,
                )

        cache = PoTokenCache(
            cache_providers=[pcp_one, pcp_two],
            cache_spec_providers=[WriteFirstPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN))
        assert pcp_one.store_calls == 1
        assert pcp_two.store_calls == 0

    def test_store_write_all_policy_cache_spec(self, pot_request, ie, logger):
        pcp_one = create_memory_pcp(ie, logger, provider_key='memory_pcp_one')
        pcp_two = create_memory_pcp(ie, logger, provider_key='memory_pcp_two')

        class WriteAllPCSP(BaseMockCacheSpecProvider):
            def generate_cache_spec(self, request: PoTokenRequest):
                super().generate_cache_spec(request)
                return PoTokenCacheSpec(
                    key_bindings={'v': request.video_id, 'e': None},
                    default_ttl=60,
                    write_policy=CacheProviderWritePolicy.WRITE_ALL,
                )

        cache = PoTokenCache(
            cache_providers=[pcp_one, pcp_two],
            cache_spec_providers=[WriteAllPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN))
        assert pcp_one.store_calls == 1
        assert pcp_two.store_calls == 1

    def test_expires_at_pot_response(self, pot_request, memorypcp, ie, logger):
        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=10000000000)
        cache.store(pot_request, response)
        assert next(iter(memorypcp.cache.values()))[1] == 10000000000

    def test_expires_at_default_spec(self, pot_request, memorypcp, ie, logger):

        class TtlPCSP(BaseMockCacheSpecProvider):
            def generate_cache_spec(self, request: PoTokenRequest):
                super().generate_cache_spec(request)
                return PoTokenCacheSpec(
                    key_bindings={'v': request.video_id, 'e': None},
                    default_ttl=10000000000,
                )

        cache = PoTokenCache(
            cache_providers=[memorypcp],
            cache_spec_providers=[TtlPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response)
        assert next(iter(memorypcp.cache.values()))[1] >= 10000000000

    def test_cache_provider_error_no_fallback(self, pot_request, ie, logger):
        error_pcp = ErrorPCP(ie, logger, {})
        cache = PoTokenCache(
            cache_providers=[error_pcp],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response)
        assert cache.get(pot_request) is None
        assert error_pcp.get_calls == 1
        assert error_pcp.store_calls == 1

        assert logger.messages['warning'].count("Error from \"error\" PO Token cache provider: PoTokenCacheProviderError('something went wrong'); example bug report message") == 2

    def test_cache_provider_error_fallback(self, pot_request, ie, logger):
        error_pcp = ErrorPCP(ie, logger, {})
        memory_pcp = create_memory_pcp(ie, logger, provider_key='memory')

        cache = PoTokenCache(
            cache_providers=[error_pcp, memory_pcp],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response)

        # 1. Store fails for error_pcp, stored in memory_pcp
        # 2. Get fails for error_pcp, fetched from memory_pcp
        # 3. Since fetched from lower priority, it should be stored in the highest priority cache provider
        # 4. Store fails in error_pcp. Since write policy is WRITE_FIRST, it should not try to store in memory_pcp regardless of if the store in error_pcp fails

        assert cache.get(pot_request)
        assert error_pcp.get_calls == 1
        assert error_pcp.store_calls == 2  # since highest priority, when fetched from lower priority, it should be stored in the highest priority cache provider
        assert memory_pcp.get_calls == 1
        assert memory_pcp.store_calls == 1

        assert logger.messages['warning'].count("Error from \"error\" PO Token cache provider: PoTokenCacheProviderError('something went wrong'); example bug report message") == 3

    def test_cache_provider_unexpected_error_no_fallback(self, pot_request, ie, logger):
        error_pcp = UnexpectedErrorPCP(ie, logger, {})
        cache = PoTokenCache(
            cache_providers=[error_pcp],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response)
        assert cache.get(pot_request) is None
        assert error_pcp.get_calls == 1
        assert error_pcp.store_calls == 1

        assert logger.messages['error'].count("Error occurred with \"unexpected_error\" PO Token cache provider: ValueError('something went wrong'); example bug report message") == 2

    def test_cache_provider_unexpected_error_fallback(self, pot_request, ie, logger):
        error_pcp = UnexpectedErrorPCP(ie, logger, {})
        memory_pcp = create_memory_pcp(ie, logger, provider_key='memory')

        cache = PoTokenCache(
            cache_providers=[error_pcp, memory_pcp],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response)

        # 1. Store fails for error_pcp, stored in memory_pcp
        # 2. Get fails for error_pcp, fetched from memory_pcp
        # 3. Since fetched from lower priority, it should be stored in the highest priority cache provider
        # 4. Store fails in error_pcp. Since write policy is WRITE_FIRST, it should not try to store in memory_pcp regardless of if the store in error_pcp fails

        assert cache.get(pot_request)
        assert error_pcp.get_calls == 1
        assert error_pcp.store_calls == 2  # since highest priority, when fetched from lower priority, it should be stored in the highest priority cache provider
        assert memory_pcp.get_calls == 1
        assert memory_pcp.store_calls == 1

        assert logger.messages['error'].count("Error occurred with \"unexpected_error\" PO Token cache provider: ValueError('something went wrong'); example bug report message") == 3

    def test_cache_provider_unavailable_no_fallback(self, pot_request, ie, logger):
        provider = create_memory_pcp(ie, logger, available=False)

        cache = PoTokenCache(
            cache_providers=[provider],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response)
        assert cache.get(pot_request) is None
        assert provider.get_calls == 0
        assert provider.store_calls == 0
        assert provider.available_called_times

    def test_cache_provider_unavailable_fallback(self, pot_request, ie, logger):
        provider_unavailable = create_memory_pcp(ie, logger, provider_key='unavailable', provider_name='unavailable', available=False)
        provider_available = create_memory_pcp(ie, logger, provider_key='available', provider_name='available')

        cache = PoTokenCache(
            cache_providers=[provider_unavailable, provider_available],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response)
        assert cache.get(pot_request) is not None
        assert provider_unavailable.get_calls == 0
        assert provider_unavailable.store_calls == 0
        assert provider_available.get_calls == 1
        assert provider_available.store_calls == 1
        assert provider_unavailable.available_called_times
        assert provider_available.available_called_times

        # should not even try to use the provider for the request
        assert 'Attempting to fetch a PO Token response from "unavailable" provider' not in logger.messages['trace']
        assert 'Attempting to fetch a PO Token response from "available" provider' not in logger.messages['trace']

    def test_available_not_called(self, ie, pot_request, logger):
        # Test that the available method is not called when provider higher in the list is available
        provider_unavailable = create_memory_pcp(
            ie, logger, provider_key='unavailable', provider_name='unavailable', available=False)
        provider_available = create_memory_pcp(ie, logger, provider_key='available', provider_name='available')

        logger.log_level = logger.LogLevel.INFO

        cache = PoTokenCache(
            cache_providers=[provider_available, provider_unavailable],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response, write_policy=CacheProviderWritePolicy.WRITE_FIRST)
        assert cache.get(pot_request) is not None
        assert provider_unavailable.get_calls == 0
        assert provider_unavailable.store_calls == 0
        assert provider_available.get_calls == 1
        assert provider_available.store_calls == 1
        assert provider_unavailable.available_called_times == 0
        assert provider_available.available_called_times
        assert 'PO Token Cache Providers: available-0.0.0 (external), unavailable-0.0.0 (external, unavailable)' not in logger.messages.get('trace', [])

    def test_available_called_trace(self, ie, pot_request, logger):
        # But if logging level is trace should call available (as part of debug logging)
        provider_unavailable = create_memory_pcp(
            ie, logger, provider_key='unavailable', provider_name='unavailable', available=False)
        provider_available = create_memory_pcp(ie, logger, provider_key='available', provider_name='available')

        logger.log_level = logger.LogLevel.TRACE

        cache = PoTokenCache(
            cache_providers=[provider_available, provider_unavailable],
            cache_spec_providers=[ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})],
            logger=logger,
        )

        response = PoTokenResponse(EXAMPLE_PO_TOKEN)
        cache.store(pot_request, response, write_policy=CacheProviderWritePolicy.WRITE_FIRST)
        assert cache.get(pot_request) is not None
        assert provider_unavailable.get_calls == 0
        assert provider_unavailable.store_calls == 0
        assert provider_available.get_calls == 1
        assert provider_available.store_calls == 1
        assert provider_unavailable.available_called_times
        assert provider_available.available_called_times
        assert 'PO Token Cache Providers: available-0.0.0 (external), unavailable-0.0.0 (external, unavailable)' in logger.messages.get('trace', [])

    def test_close(self, ie, pot_request, logger):
        # Should call close on the cache providers and cache specs
        memory_pcp = create_memory_pcp(ie, logger, provider_key='memory')
        memory2_pcp = create_memory_pcp(ie, logger, provider_key='memory2')

        spec1 = ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        spec2 = UnavailableCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})

        cache = PoTokenCache(
            cache_providers=[memory2_pcp, memory_pcp],
            cache_spec_providers=[spec1, spec2],
            logger=logger,
        )

        cache.close()
        assert memory_pcp.close_called
        assert memory2_pcp.close_called
        assert spec1.close_called
        assert spec2.close_called


class TestPoTokenRequestDirector:

    def test_request_pot_success(self, ie, pot_request, pot_cache, pot_provider, logger):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        director.register_provider(pot_provider)
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN

    def test_request_and_cache(self, ie, pot_request, pot_cache, pot_provider, logger):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        director.register_provider(pot_provider)
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_provider.request_called_times == 1
        assert pot_cache.get_calls == 1
        assert pot_cache.store_calls == 1

        # Second request, should be cached
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_cache.get_calls == 2
        assert pot_cache.store_calls == 1
        assert pot_provider.request_called_times == 1

    def test_bypass_cache(self, ie, pot_request, pot_cache, logger, pot_provider):
        pot_request.bypass_cache = True

        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        director.register_provider(pot_provider)
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_provider.request_called_times == 1
        assert pot_cache.get_calls == 0
        assert pot_cache.store_calls == 1

        # Second request, should not get from cache
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_provider.request_called_times == 2
        assert pot_cache.get_calls == 0
        assert pot_cache.store_calls == 2

        # POT is still cached, should get from cache
        pot_request.bypass_cache = False
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_provider.request_called_times == 2
        assert pot_cache.get_calls == 1
        assert pot_cache.store_calls == 2

    def test_clean_pot_generate(self, ie, pot_request, pot_cache, logger):
        # Token should be cleaned before returning
        base_token = base64.urlsafe_b64encode(b'token').decode()
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = success_ptp(PoTokenResponse(base_token + '?extra=params'))(ie, logger, settings={})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response == base_token
        assert provider.request_called_times == 1

        # Confirm the cleaned version was stored in the cache
        cached_token = pot_cache.get(pot_request)
        assert cached_token.po_token == base_token

    def test_clean_pot_cache(self, ie, pot_request, pot_cache, logger, pot_provider):
        # Token retrieved from cache should be cleaned before returning
        base_token = base64.urlsafe_b64encode(b'token').decode()
        pot_cache.store(pot_request, PoTokenResponse(base_token + '?extra=params'))
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        director.register_provider(pot_provider)

        response = director.get_po_token(pot_request)
        assert response == base_token
        assert pot_cache.get_calls == 1
        assert pot_provider.request_called_times == 0

    def test_cache_expires_at_none(self, ie, pot_request, pot_cache, logger, pot_provider):
        # Should cache if expires_at=None in the response
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = success_ptp(PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=None))(ie, logger, settings={})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_cache.store_calls == 1
        assert pot_cache.get(pot_request).po_token == EXAMPLE_PO_TOKEN

    def test_cache_expires_at_positive(self, ie, pot_request, pot_cache, logger, pot_provider):
        # Should cache if expires_at is a positive number in the response
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = success_ptp(PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=99999999999))(ie, logger, settings={})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_cache.store_calls == 1
        assert pot_cache.get(pot_request).po_token == EXAMPLE_PO_TOKEN

    @pytest.mark.parametrize('expires_at', [0, -1])
    def test_not_cache_expires_at(self, ie, pot_request, pot_cache, logger, pot_provider, expires_at):
        # Should not cache if expires_at <= 0 in the response
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = success_ptp(PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=expires_at))(ie, logger, settings={})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert pot_cache.store_calls == 0
        assert pot_cache.get(pot_request) is None

    def test_no_providers(self, ie, pot_request, pot_cache, logger):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        response = director.get_po_token(pot_request)
        assert response is None

    def test_try_cache_no_providers(self, ie, pot_request, pot_cache, logger):
        # Should still try the cache even if no providers are configured
        pot_cache.store(pot_request, PoTokenResponse(EXAMPLE_PO_TOKEN))
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN

    def test_close(self, ie, pot_request, pot_cache, pot_provider, logger):
        # Should call close on the pot cache and any providers
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)

        provider2 = UnavailablePTP(ie, logger, {})
        director.register_provider(pot_provider)
        director.register_provider(provider2)

        director.close()
        assert pot_provider.close_called
        assert provider2.close_called
        assert pot_cache.close_called

    def test_pot_provider_preferences(self, pot_request, pot_cache, ie, logger):
        pot_request.bypass_cache = True
        provider_two_pot = base64.urlsafe_b64encode(b'token2').decode()

        example_provider = success_ptp(response=PoTokenResponse(EXAMPLE_PO_TOKEN), key='exampleone')(ie, logger, settings={})
        example_provider_two = success_ptp(response=PoTokenResponse(provider_two_pot), key='exampletwo')(ie, logger, settings={})

        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        director.register_provider(example_provider)
        director.register_provider(example_provider_two)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert example_provider.request_called_times == 1
        assert example_provider_two.request_called_times == 0

        standard_preference_called = False
        example_preference_called = False

        # Test that the provider preferences are respected
        def standard_preference(provider, request, *_, **__):
            nonlocal standard_preference_called
            standard_preference_called = True
            assert isinstance(provider, PoTokenProvider)
            assert isinstance(request, PoTokenRequest)
            return 1

        def example_preference(provider, request, *_, **__):
            nonlocal example_preference_called
            example_preference_called = True
            assert isinstance(provider, PoTokenProvider)
            assert isinstance(request, PoTokenRequest)
            if provider.PROVIDER_KEY == example_provider.PROVIDER_KEY:
                return -100
            return 0

        # test that it can handle multiple preferences
        director.register_preference(example_preference)
        director.register_preference(standard_preference)

        response = director.get_po_token(pot_request)
        assert response == provider_two_pot
        assert example_provider.request_called_times == 1
        assert example_provider_two.request_called_times == 1
        assert standard_preference_called
        assert example_preference_called

    def test_unsupported_request_no_fallback(self, ie, logger, pot_cache, pot_request):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnsupportedPTP(ie, logger, {})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response is None
        assert provider.request_called_times == 1

    def test_unsupported_request_fallback(self, ie, logger, pot_cache, pot_request, pot_provider):
        # Should fallback to the next provider if the first one does not support the request
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnsupportedPTP(ie, logger, {})
        director.register_provider(provider)
        director.register_provider(pot_provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 1
        assert pot_provider.request_called_times == 1
        assert 'PO Token Provider "unsupported" rejected this request, trying next available provider. Reason: unsupported request' in logger.messages['trace']

    def test_unavailable_request_no_fallback(self, ie, logger, pot_cache, pot_request):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnavailablePTP(ie, logger, {})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response is None
        assert provider.request_called_times == 0
        assert provider.available_called_times

    def test_unavailable_request_fallback(self, ie, logger, pot_cache, pot_request, pot_provider):
        # Should fallback to the next provider if the first one is unavailable
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnavailablePTP(ie, logger, {})
        director.register_provider(provider)
        director.register_provider(pot_provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 0
        assert provider.available_called_times
        assert pot_provider.request_called_times == 1
        assert pot_provider.available_called_times
        # should not even try use the provider for the request
        assert 'Attempting to fetch a PO Token from "unavailable" provider' not in logger.messages['trace']
        assert 'Attempting to fetch a PO Token from "success" provider' in logger.messages['trace']

    def test_available_not_called(self, ie, logger, pot_cache, pot_request, pot_provider):
        # Test that the available method is not called when provider higher in the list is available
        logger.log_level = logger.LogLevel.INFO
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnavailablePTP(ie, logger, {})
        director.register_provider(pot_provider)
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 0
        assert provider.available_called_times == 0
        assert pot_provider.request_called_times == 1
        assert pot_provider.available_called_times == 2
        assert 'PO Token Providers: success-0.0.1 (external), unavailable-0.0.0 (external, unavailable)' not in logger.messages.get('trace', [])

    def test_available_called_trace(self, ie, logger, pot_cache, pot_request, pot_provider):
        # But if logging level is trace should call available (as part of debug logging)
        logger.log_level = logger.LogLevel.TRACE
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnavailablePTP(ie, logger, {})
        director.register_provider(pot_provider)
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 0
        assert provider.available_called_times == 1
        assert pot_provider.request_called_times == 1
        assert pot_provider.available_called_times == 3
        assert 'PO Token Providers: success-0.0.1 (external), unavailable-0.0.0 (external, unavailable)' in logger.messages['trace']

    def test_provider_error_no_fallback_unexpected(self, ie, logger, pot_cache, pot_request):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = ErrorPTP(ie, logger, {})
        director.register_provider(provider)
        pot_request.video_id = 'unexpected'
        response = director.get_po_token(pot_request)
        assert response is None
        assert provider.request_called_times == 1
        assert "Error fetching PO Token from \"error\" provider: PoTokenProviderError('an error occurred'); please report this issue to the provider developer at  https://error.example.com/issues  ." in logger.messages['warning']

    def test_provider_error_no_fallback_expected(self, ie, logger, pot_cache, pot_request):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = ErrorPTP(ie, logger, {})
        director.register_provider(provider)
        pot_request.video_id = 'expected'
        response = director.get_po_token(pot_request)
        assert response is None
        assert provider.request_called_times == 1
        assert "Error fetching PO Token from \"error\" provider: PoTokenProviderError('an error occurred')" in logger.messages['warning']

    def test_provider_error_fallback(self, ie, logger, pot_cache, pot_request, pot_provider):
        # Should fallback to the next provider if the first one raises an error
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = ErrorPTP(ie, logger, {})
        director.register_provider(provider)
        director.register_provider(pot_provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 1
        assert pot_provider.request_called_times == 1
        assert "Error fetching PO Token from \"error\" provider: PoTokenProviderError('an error occurred'); please report this issue to the provider developer at  https://error.example.com/issues  ." in logger.messages['warning']

    def test_provider_unexpected_error_no_fallback(self, ie, logger, pot_cache, pot_request):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnexpectedErrorPTP(ie, logger, {})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response is None
        assert provider.request_called_times == 1
        assert "Unexpected error when fetching PO Token from \"unexpected_error\" provider: ValueError('an unexpected error occurred'); please report this issue to the provider developer at  https://unexpected.example.com/issues  ." in logger.messages['error']

    def test_provider_unexpected_error_fallback(self, ie, logger, pot_cache, pot_request, pot_provider):
        # Should fallback to the next provider if the first one raises an unexpected error
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = UnexpectedErrorPTP(ie, logger, {})
        director.register_provider(provider)
        director.register_provider(pot_provider)

        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 1
        assert pot_provider.request_called_times == 1
        assert "Unexpected error when fetching PO Token from \"unexpected_error\" provider: ValueError('an unexpected error occurred'); please report this issue to the provider developer at  https://unexpected.example.com/issues  ." in logger.messages['error']

    def test_invalid_po_token_response_type(self, ie, logger, pot_cache, pot_request, pot_provider):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = InvalidPTP(ie, logger, {})
        director.register_provider(provider)

        pot_request.video_id = 'invalid_type'

        response = director.get_po_token(pot_request)
        assert response is None
        assert provider.request_called_times == 1
        assert 'Invalid PO Token response received from "invalid" provider: invalid-response; please report this issue to the provider developer at  https://invalid.example.com/issues  .' in logger.messages['error']

        # Should fallback to next available provider
        director.register_provider(pot_provider)
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 2
        assert pot_provider.request_called_times == 1

    def test_invalid_po_token_response(self, ie, logger, pot_cache, pot_request, pot_provider):
        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)
        provider = InvalidPTP(ie, logger, {})
        director.register_provider(provider)

        response = director.get_po_token(pot_request)
        assert response is None
        assert provider.request_called_times == 1
        assert "Invalid PO Token response received from \"invalid\" provider: PoTokenResponse(po_token='example-token?', expires_at='123'); please report this issue to the provider developer at  https://invalid.example.com/issues  ." in logger.messages['error']

        # Should fallback to next available provider
        director.register_provider(pot_provider)
        response = director.get_po_token(pot_request)
        assert response == EXAMPLE_PO_TOKEN
        assert provider.request_called_times == 2
        assert pot_provider.request_called_times == 1

    def test_copy_request_provider(self, ie, logger, pot_cache, pot_request):

        class BadProviderPTP(BaseMockPoTokenProvider):
            _SUPPORTED_CONTEXTS = None
            _SUPPORTED_CLIENTS = None

            def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
                # Providers should not modify the request object, but we should guard against it
                request.video_id = 'bad'
                raise PoTokenProviderRejectedRequest('bad request')

        class GoodProviderPTP(BaseMockPoTokenProvider):
            _SUPPORTED_CONTEXTS = None
            _SUPPORTED_CLIENTS = None

            def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
                return PoTokenResponse(base64.urlsafe_b64encode(request.video_id.encode()).decode())

        director = PoTokenRequestDirector(logger=logger, cache=pot_cache)

        bad_provider = BadProviderPTP(ie, logger, {})
        good_provider = GoodProviderPTP(ie, logger, {})

        director.register_provider(bad_provider)
        director.register_provider(good_provider)

        pot_request.video_id = 'good'
        response = director.get_po_token(pot_request)
        assert response == base64.urlsafe_b64encode(b'good').decode()
        assert bad_provider.request_called_times == 1
        assert good_provider.request_called_times == 1
        assert pot_request.video_id == 'good'


@pytest.mark.parametrize('spec, expected', [
    (None, False),
    (PoTokenCacheSpec(key_bindings={'v': 'video-id'}, default_ttl=60, write_policy=None), False),  # type: ignore
    (PoTokenCacheSpec(key_bindings={'v': 'video-id'}, default_ttl='invalid'), False),  # type: ignore
    (PoTokenCacheSpec(key_bindings='invalid', default_ttl=60), False),  # type: ignore
    (PoTokenCacheSpec(key_bindings={2: 'video-id'}, default_ttl=60), False),  # type: ignore
    (PoTokenCacheSpec(key_bindings={'v': 2}, default_ttl=60), False),  # type: ignore
    (PoTokenCacheSpec(key_bindings={'v': None}, default_ttl=60), False),  # type: ignore

    (PoTokenCacheSpec(key_bindings={'v': 'video_id', 'e': None}, default_ttl=60), True),
    (PoTokenCacheSpec(key_bindings={'v': 'video_id'}, default_ttl=60, write_policy=CacheProviderWritePolicy.WRITE_FIRST), True),
])
def test_validate_cache_spec(spec, expected):
    assert validate_cache_spec(spec) == expected


@pytest.mark.parametrize('po_token', [
    'invalid-token?',
    '123',
])
def test_clean_pot_fail(po_token):
    with pytest.raises(ValueError, match='Invalid PO Token'):
        clean_pot(po_token)


@pytest.mark.parametrize('po_token,expected', [
    ('TwAA/+8=', 'TwAA_-8='),
    ('TwAA%5F%2D9VA6Q92v%5FvEQ4==?extra-param=2', 'TwAA_-9VA6Q92v_vEQ4='),
])
def test_clean_pot(po_token, expected):
    assert clean_pot(po_token) == expected


@pytest.mark.parametrize(
    'response, expected',
    [
        (None, False),
        (PoTokenResponse(None), False),
        (PoTokenResponse(1), False),
        (PoTokenResponse('invalid-token?'), False),
        (PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at='abc'), False),  # type: ignore
        (PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=100), False),
        (PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=time.time() + 10000.0), False),  # type: ignore
        (PoTokenResponse(EXAMPLE_PO_TOKEN), True),
        (PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=-1), True),
        (PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=0), True),
        (PoTokenResponse(EXAMPLE_PO_TOKEN, expires_at=int(time.time()) + 10000), True),
    ],
)
def test_validate_pot_response(response, expected):
    assert validate_response(response) == expected


def test_built_in_provider(ie, logger):
    class BuiltinProviderDefaultT(BuiltinIEContentProvider, suffix='T'):
        def is_available(self):
            return True

    class BuiltinProviderCustomNameT(BuiltinIEContentProvider, suffix='T'):
        PROVIDER_NAME = 'CustomName'

        def is_available(self):
            return True

    class ExternalProviderDefaultT(IEContentProvider, suffix='T'):
        def is_available(self):
            return True

    class ExternalProviderCustomT(IEContentProvider, suffix='T'):
        PROVIDER_NAME = 'custom'
        PROVIDER_VERSION = '5.4b2'

        def is_available(self):
            return True

    class ExternalProviderUnavailableT(IEContentProvider, suffix='T'):
        def is_available(self) -> bool:
            return False

    class BuiltinProviderUnavailableT(IEContentProvider, suffix='T'):
        def is_available(self) -> bool:
            return False

    built_in_default = BuiltinProviderDefaultT(ie=ie, logger=logger, settings={})
    built_in_custom_name = BuiltinProviderCustomNameT(ie=ie, logger=logger, settings={})
    built_in_unavailable = BuiltinProviderUnavailableT(ie=ie, logger=logger, settings={})
    external_default = ExternalProviderDefaultT(ie=ie, logger=logger, settings={})
    external_custom = ExternalProviderCustomT(ie=ie, logger=logger, settings={})
    external_unavailable = ExternalProviderUnavailableT(ie=ie, logger=logger, settings={})

    assert provider_display_list([]) == 'none'
    assert provider_display_list([built_in_default]) == 'BuiltinProviderDefault'
    assert provider_display_list([external_unavailable]) == 'ExternalProviderUnavailable-0.0.0 (external, unavailable)'
    assert provider_display_list([
        built_in_default,
        built_in_custom_name,
        external_default,
        external_custom,
        external_unavailable,
        built_in_unavailable],
    ) == 'BuiltinProviderDefault, CustomName, ExternalProviderDefault-0.0.0 (external), custom-5.4b2 (external), ExternalProviderUnavailable-0.0.0 (external, unavailable), BuiltinProviderUnavailable-0.0.0 (external, unavailable)'
