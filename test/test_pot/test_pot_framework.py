import pytest

from yt_dlp.extractor.youtube.pot._provider import IEContentProvider
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.utils.networking import HTTPHeaderDict
from yt_dlp.extractor.youtube.pot.provider import (
    PoTokenRequest,
    PoTokenContext,
    ExternalRequestFeature,

)

from yt_dlp.extractor.youtube.pot.cache import (
    PoTokenCacheProvider,
    PoTokenCacheSpec,
    PoTokenCacheSpecProvider,
    CacheProviderWritePolicy,
)

import yt_dlp.extractor.youtube.pot.cache as cache

from yt_dlp.networking import Request
from yt_dlp.extractor.youtube.pot.provider import (
    PoTokenResponse,
    PoTokenProvider,
    PoTokenProviderRejectedRequest,
    provider_bug_report_message,
    register_provider,
    register_preference,
)

from yt_dlp.extractor.youtube.pot._registry import _pot_providers, _ptp_preferences, _pot_pcs_providers, _pot_cache_providers, _pot_cache_provider_preferences


class ExamplePTP(PoTokenProvider):
    PROVIDER_NAME = 'example'
    PROVIDER_VERSION = '0.0.1'
    BUG_REPORT_LOCATION = 'https://example.com/issues'

    _SUPPORTED_CLIENTS = ('WEB',)
    _SUPPORTED_CONTEXTS = (PoTokenContext.GVS, )

    _SUPPORTED_EXTERNAL_REQUEST_FEATURES = (
        ExternalRequestFeature.PROXY_SCHEME_HTTP,
        ExternalRequestFeature.PROXY_SCHEME_SOCKS5H,
    )

    def is_available(self) -> bool:
        return True

    def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
        return PoTokenResponse('example-token', expires_at=123)


class ExampleCacheProviderPCP(PoTokenCacheProvider):

    PROVIDER_NAME = 'example'
    PROVIDER_VERSION = '0.0.1'
    BUG_REPORT_LOCATION = 'https://example.com/issues'

    def is_available(self) -> bool:
        return True

    def get(self, key: str):
        return 'example-cache'

    def store(self, key: str, value: str, expires_at: int):
        pass

    def delete(self, key: str):
        pass


class ExampleCacheSpecProviderPCSP(PoTokenCacheSpecProvider):

    PROVIDER_NAME = 'example'
    PROVIDER_VERSION = '0.0.1'
    BUG_REPORT_LOCATION = 'https://example.com/issues'

    def generate_cache_spec(self, request: PoTokenRequest):
        return PoTokenCacheSpec(
            key_bindings={'field': 'example-key'},
            default_ttl=60,
            write_policy=CacheProviderWritePolicy.WRITE_FIRST,
        )


class TestPoTokenProvider:

    def test_base_type(self):
        assert issubclass(PoTokenProvider, IEContentProvider)

    def test_create_provider_missing_fetch_method(self, ie, logger):
        class MissingMethodsPTP(PoTokenProvider):
            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            MissingMethodsPTP(ie=ie, logger=logger, settings={})

    def test_create_provider_missing_available_method(self, ie, logger):
        class MissingMethodsPTP(PoTokenProvider):
            def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
                raise PoTokenProviderRejectedRequest('Not implemented')

        with pytest.raises(TypeError):
            MissingMethodsPTP(ie=ie, logger=logger, settings={})

    def test_barebones_provider(self, ie, logger):
        class BarebonesProviderPTP(PoTokenProvider):
            def is_available(self) -> bool:
                return True

            def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
                raise PoTokenProviderRejectedRequest('Not implemented')

        provider = BarebonesProviderPTP(ie=ie, logger=logger, settings={})
        assert provider.PROVIDER_NAME == 'BarebonesProvider'
        assert provider.PROVIDER_KEY == 'BarebonesProvider'
        assert provider.PROVIDER_VERSION == '0.0.0'
        assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  (developer has not provided a bug report location)  .'

    def test_example_provider_success(self, ie, logger, pot_request):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})
        assert provider.PROVIDER_NAME == 'example'
        assert provider.PROVIDER_KEY == 'Example'
        assert provider.PROVIDER_VERSION == '0.0.1'
        assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  https://example.com/issues  .'
        assert provider.is_available()

        response = provider.request_pot(pot_request)

        assert response.po_token == 'example-token'
        assert response.expires_at == 123

    def test_provider_unsupported_context(self, ie, logger, pot_request):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})
        pot_request.context = PoTokenContext.PLAYER

        with pytest.raises(PoTokenProviderRejectedRequest):
            provider.request_pot(pot_request)

    def test_provider_unsupported_client(self, ie, logger, pot_request):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})
        pot_request.innertube_context['client']['clientName'] = 'ANDROID'

        with pytest.raises(PoTokenProviderRejectedRequest):
            provider.request_pot(pot_request)

    def test_provider_unsupported_proxy_scheme(self, ie, logger, pot_request):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})
        pot_request.request_proxy = 'socks4://example.com'

        with pytest.raises(
            PoTokenProviderRejectedRequest,
            match='External requests by "example" provider do not support proxy scheme "socks4". Supported proxy '
            'schemes: http, socks5h',
        ):
            provider.request_pot(pot_request)

        pot_request.request_proxy = 'http://example.com'

        assert provider.request_pot(pot_request)

    def test_provider_ignore_external_request_features(self, ie, logger, pot_request):
        class InternalPTP(ExamplePTP):
            _SUPPORTED_EXTERNAL_REQUEST_FEATURES = None

        provider = InternalPTP(ie=ie, logger=logger, settings={})

        pot_request.request_proxy = 'socks5://example.com'
        assert provider.request_pot(pot_request)
        pot_request.request_source_address = '0.0.0.0'
        assert provider.request_pot(pot_request)

    def test_provider_unsupported_external_request_source_address(self, ie, logger, pot_request):
        class InternalPTP(ExamplePTP):
            _SUPPORTED_EXTERNAL_REQUEST_FEATURES = tuple()

        provider = InternalPTP(ie=ie, logger=logger, settings={})

        pot_request.request_source_address = None
        assert provider.request_pot(pot_request)

        pot_request.request_source_address = '0.0.0.0'
        with pytest.raises(
            PoTokenProviderRejectedRequest,
            match='External requests by "example" provider do not support setting source address',
        ):
            provider.request_pot(pot_request)

    def test_provider_supported_external_request_source_address(self, ie, logger, pot_request):
        class InternalPTP(ExamplePTP):
            _SUPPORTED_EXTERNAL_REQUEST_FEATURES = (
                ExternalRequestFeature.SOURCE_ADDRESS,
            )

        provider = InternalPTP(ie=ie, logger=logger, settings={})

        pot_request.request_source_address = None
        assert provider.request_pot(pot_request)

        pot_request.request_source_address = '0.0.0.0'
        assert provider.request_pot(pot_request)

    def test_provider_unsupported_external_request_tls_verification(self, ie, logger, pot_request):
        class InternalPTP(ExamplePTP):
            _SUPPORTED_EXTERNAL_REQUEST_FEATURES = tuple()

        provider = InternalPTP(ie=ie, logger=logger, settings={})

        pot_request.request_verify_tls = True
        assert provider.request_pot(pot_request)

        pot_request.request_verify_tls = False
        with pytest.raises(
            PoTokenProviderRejectedRequest,
            match='External requests by "example" provider do not support ignoring TLS certificate failures',
        ):
            provider.request_pot(pot_request)

    def test_provider_supported_external_request_tls_verification(self, ie, logger, pot_request):
        class InternalPTP(ExamplePTP):
            _SUPPORTED_EXTERNAL_REQUEST_FEATURES = (
                ExternalRequestFeature.DISABLE_TLS_VERIFICATION,
            )

        provider = InternalPTP(ie=ie, logger=logger, settings={})

        pot_request.request_verify_tls = True
        assert provider.request_pot(pot_request)

        pot_request.request_verify_tls = False
        assert provider.request_pot(pot_request)

    def test_provider_request_webpage(self, ie, logger, pot_request):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})

        cookiejar = YoutubeDLCookieJar()
        pot_request.request_headers = HTTPHeaderDict({'User-Agent': 'example-user-agent'})
        pot_request.request_proxy = 'socks5://example-proxy.com'
        pot_request.request_cookiejar = cookiejar

        def mock_urlopen(request):
            return request

        ie._downloader.urlopen = mock_urlopen

        sent_request = provider._request_webpage(Request(
            'https://example.com',
        ), pot_request=pot_request)

        assert sent_request.url == 'https://example.com'
        assert sent_request.headers['User-Agent'] == 'example-user-agent'
        assert sent_request.proxies == {'all': 'socks5://example-proxy.com'}
        assert sent_request.extensions['cookiejar'] is cookiejar
        assert 'Requesting webpage' in logger.messages['info']

    def test_provider_request_webpage_override(self, ie, logger, pot_request):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})

        cookiejar_request = YoutubeDLCookieJar()
        pot_request.request_headers = HTTPHeaderDict({'User-Agent': 'example-user-agent'})
        pot_request.request_proxy = 'socks5://example-proxy.com'
        pot_request.request_cookiejar = cookiejar_request

        def mock_urlopen(request):
            return request

        ie._downloader.urlopen = mock_urlopen

        sent_request = provider._request_webpage(Request(
            'https://example.com',
            headers={'User-Agent': 'override-user-agent-override'},
            proxies={'http': 'http://example-proxy-override.com'},
            extensions={'cookiejar': YoutubeDLCookieJar()},
        ), pot_request=pot_request, note='Custom requesting webpage')

        assert sent_request.url == 'https://example.com'
        assert sent_request.headers['User-Agent'] == 'override-user-agent-override'
        assert sent_request.proxies == {'http': 'http://example-proxy-override.com'}
        assert sent_request.extensions['cookiejar'] is not cookiejar_request
        assert 'Custom requesting webpage' in logger.messages['info']

    def test_provider_request_webpage_no_log(self, ie, logger, pot_request):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})

        def mock_urlopen(request):
            return request

        ie._downloader.urlopen = mock_urlopen

        sent_request = provider._request_webpage(Request(
            'https://example.com',
        ), note=False)

        assert sent_request.url == 'https://example.com'
        assert 'info' not in logger.messages

    def test_provider_request_webpage_no_pot_request(self, ie, logger):
        provider = ExamplePTP(ie=ie, logger=logger, settings={})

        def mock_urlopen(request):
            return request

        ie._downloader.urlopen = mock_urlopen

        sent_request = provider._request_webpage(Request(
            'https://example.com',
        ), pot_request=None)

        assert sent_request.url == 'https://example.com'

    def test_get_config_arg(self, ie, logger):
        provider = ExamplePTP(ie=ie, logger=logger, settings={'abc': ['123D'], 'xyz': ['456a', '789B']})

        assert provider._configuration_arg('abc') == ['123d']
        assert provider._configuration_arg('abc', default=['default']) == ['123d']
        assert provider._configuration_arg('ABC', default=['default']) == ['default']
        assert provider._configuration_arg('abc', casesense=True) == ['123D']
        assert provider._configuration_arg('xyz', casesense=False) == ['456a', '789b']

    def test_require_class_end_with_suffix(self, ie, logger):
        class InvalidSuffix(PoTokenProvider):
            PROVIDER_NAME = 'invalid-suffix'

            def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
                raise PoTokenProviderRejectedRequest('Not implemented')

            def is_available(self) -> bool:
                return True

        provider = InvalidSuffix(ie=ie, logger=logger, settings={})

        with pytest.raises(AssertionError):
            provider.PROVIDER_KEY  # noqa: B018


class TestPoTokenCacheProvider:

    def test_base_type(self):
        assert issubclass(PoTokenCacheProvider, IEContentProvider)

    def test_create_provider_missing_get_method(self, ie, logger):
        class MissingMethodsPCP(PoTokenCacheProvider):
            def store(self, key: str, value: str, expires_at: int):
                pass

            def delete(self, key: str):
                pass

                def is_available(self) -> bool:
                    return True

        with pytest.raises(TypeError):
            MissingMethodsPCP(ie=ie, logger=logger, settings={})

    def test_create_provider_missing_store_method(self, ie, logger):
        class MissingMethodsPCP(PoTokenCacheProvider):
            def get(self, key: str):
                pass

            def delete(self, key: str):
                pass

            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            MissingMethodsPCP(ie=ie, logger=logger, settings={})

    def test_create_provider_missing_delete_method(self, ie, logger):
        class MissingMethodsPCP(PoTokenCacheProvider):
            def get(self, key: str):
                pass

            def store(self, key: str, value: str, expires_at: int):
                pass

            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError):
            MissingMethodsPCP(ie=ie, logger=logger, settings={})

    def test_create_provider_missing_is_available_method(self, ie, logger):
        class MissingMethodsPCP(PoTokenCacheProvider):
            def get(self, key: str):
                pass

            def store(self, key: str, value: str, expires_at: int):
                pass

            def delete(self, key: str):
                pass

        with pytest.raises(TypeError):
            MissingMethodsPCP(ie=ie, logger=logger, settings={})

    def test_barebones_provider(self, ie, logger):
        class BarebonesProviderPCP(PoTokenCacheProvider):

            def is_available(self) -> bool:
                return True

            def get(self, key: str):
                return 'example-cache'

            def store(self, key: str, value: str, expires_at: int):
                pass

            def delete(self, key: str):
                pass

        provider = BarebonesProviderPCP(ie=ie, logger=logger, settings={})
        assert provider.PROVIDER_NAME == 'BarebonesProvider'
        assert provider.PROVIDER_KEY == 'BarebonesProvider'
        assert provider.PROVIDER_VERSION == '0.0.0'
        assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  (developer has not provided a bug report location)  .'

    def test_create_provider_example(self, ie, logger):
        provider = ExampleCacheProviderPCP(ie=ie, logger=logger, settings={})
        assert provider.PROVIDER_NAME == 'example'
        assert provider.PROVIDER_KEY == 'ExampleCacheProvider'
        assert provider.PROVIDER_VERSION == '0.0.1'
        assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  https://example.com/issues  .'
        assert provider.is_available()

    def test_get_config_arg(self, ie, logger):
        provider = ExampleCacheProviderPCP(ie=ie, logger=logger, settings={'abc': ['123D'], 'xyz': ['456a', '789B']})
        assert provider._configuration_arg('abc') == ['123d']
        assert provider._configuration_arg('abc', default=['default']) == ['123d']
        assert provider._configuration_arg('ABC', default=['default']) == ['default']
        assert provider._configuration_arg('abc', casesense=True) == ['123D']
        assert provider._configuration_arg('xyz', casesense=False) == ['456a', '789b']

    def test_require_class_end_with_suffix(self, ie, logger):
        class InvalidSuffix(PoTokenCacheProvider):
            def get(self, key: str):
                return 'example-cache'

            def store(self, key: str, value: str, expires_at: int):
                pass

            def delete(self, key: str):
                pass

            def is_available(self) -> bool:
                return True

        provider = InvalidSuffix(ie=ie, logger=logger, settings={})

        with pytest.raises(AssertionError):
            provider.PROVIDER_KEY  # noqa: B018


class TestPoTokenCacheSpecProvider:

    def test_base_type(self):
        assert issubclass(PoTokenCacheSpecProvider, IEContentProvider)

    def test_create_provider_missing_supports_method(self, ie, logger):
        class MissingMethodsPCS(PoTokenCacheSpecProvider):
            pass

        with pytest.raises(TypeError):
            MissingMethodsPCS(ie=ie, logger=logger, settings={})

    def test_create_provider_barebones(self, ie, pot_request, logger):
        class BarebonesProviderPCSP(PoTokenCacheSpecProvider):
            def generate_cache_spec(self, request: PoTokenRequest):
                return PoTokenCacheSpec(
                    default_ttl=100,
                    key_bindings={},
                )

        provider = BarebonesProviderPCSP(ie=ie, logger=logger, settings={})
        assert provider.PROVIDER_NAME == 'BarebonesProvider'
        assert provider.PROVIDER_KEY == 'BarebonesProvider'
        assert provider.PROVIDER_VERSION == '0.0.0'
        assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  (developer has not provided a bug report location)  .'
        assert provider.is_available()
        assert provider.generate_cache_spec(request=pot_request).default_ttl == 100
        assert provider.generate_cache_spec(request=pot_request).key_bindings == {}
        assert provider.generate_cache_spec(request=pot_request).write_policy == CacheProviderWritePolicy.WRITE_ALL

    def test_create_provider_example(self, ie, pot_request, logger):
        provider = ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={})
        assert provider.PROVIDER_NAME == 'example'
        assert provider.PROVIDER_KEY == 'ExampleCacheSpecProvider'
        assert provider.PROVIDER_VERSION == '0.0.1'
        assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  https://example.com/issues  .'
        assert provider.is_available()
        assert provider.generate_cache_spec(pot_request)
        assert provider.generate_cache_spec(pot_request).key_bindings == {'field': 'example-key'}
        assert provider.generate_cache_spec(pot_request).default_ttl == 60
        assert provider.generate_cache_spec(pot_request).write_policy == CacheProviderWritePolicy.WRITE_FIRST

    def test_get_config_arg(self, ie, logger):
        provider = ExampleCacheSpecProviderPCSP(ie=ie, logger=logger, settings={'abc': ['123D'], 'xyz': ['456a', '789B']})

        assert provider._configuration_arg('abc') == ['123d']
        assert provider._configuration_arg('abc', default=['default']) == ['123d']
        assert provider._configuration_arg('ABC', default=['default']) == ['default']
        assert provider._configuration_arg('abc', casesense=True) == ['123D']
        assert provider._configuration_arg('xyz', casesense=False) == ['456a', '789b']

    def test_require_class_end_with_suffix(self, ie, logger):
        class InvalidSuffix(PoTokenCacheSpecProvider):
            def generate_cache_spec(self, request: PoTokenRequest):
                return None

        provider = InvalidSuffix(ie=ie, logger=logger, settings={})

        with pytest.raises(AssertionError):
            provider.PROVIDER_KEY  # noqa: B018


class TestPoTokenRequest:
    def test_copy_request(self, pot_request):
        copied_request = pot_request.copy()

        assert copied_request is not pot_request
        assert copied_request.context == pot_request.context
        assert copied_request.innertube_context == pot_request.innertube_context
        assert copied_request.innertube_context is not pot_request.innertube_context
        copied_request.innertube_context['client']['clientName'] = 'ANDROID'
        assert pot_request.innertube_context['client']['clientName'] != 'ANDROID'
        assert copied_request.innertube_host == pot_request.innertube_host
        assert copied_request.session_index == pot_request.session_index
        assert copied_request.player_url == pot_request.player_url
        assert copied_request.is_authenticated == pot_request.is_authenticated
        assert copied_request.visitor_data == pot_request.visitor_data
        assert copied_request.data_sync_id == pot_request.data_sync_id
        assert copied_request.video_id == pot_request.video_id
        assert copied_request.request_cookiejar is pot_request.request_cookiejar
        assert copied_request.request_proxy == pot_request.request_proxy
        assert copied_request.request_headers == pot_request.request_headers
        assert copied_request.request_headers is not pot_request.request_headers
        assert copied_request.request_timeout == pot_request.request_timeout
        assert copied_request.request_source_address == pot_request.request_source_address
        assert copied_request.request_verify_tls == pot_request.request_verify_tls
        assert copied_request.bypass_cache == pot_request.bypass_cache


def test_provider_bug_report_message(ie, logger):
    provider = ExamplePTP(ie=ie, logger=logger, settings={})
    assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  https://example.com/issues  .'

    message = provider_bug_report_message(provider)
    assert message == '; please report this issue to the provider developer at  https://example.com/issues  .'

    message_before = provider_bug_report_message(provider, before='custom message!')
    assert message_before == 'custom message! Please report this issue to the provider developer at  https://example.com/issues  .'


def test_register_provider(ie):

    @register_provider
    class UnavailableProviderPTP(PoTokenProvider):
        def is_available(self) -> bool:
            return False

        def _real_request_pot(self, request: PoTokenRequest) -> PoTokenResponse:
            raise PoTokenProviderRejectedRequest('Not implemented')

    assert _pot_providers.value.get('UnavailableProvider') == UnavailableProviderPTP
    _pot_providers.value.pop('UnavailableProvider')


def test_register_pot_preference(ie):
    before = len(_ptp_preferences.value)

    @register_preference(ExamplePTP)
    def unavailable_preference(provider: PoTokenProvider, request: PoTokenRequest):
        return 1

    assert len(_ptp_preferences.value) == before + 1


def test_register_cache_provider(ie):

    @cache.register_provider
    class UnavailableCacheProviderPCP(PoTokenCacheProvider):
        def is_available(self) -> bool:
            return False

        def get(self, key: str):
            return 'example-cache'

        def store(self, key: str, value: str, expires_at: int):
            pass

        def delete(self, key: str):
            pass

    assert _pot_cache_providers.value.get('UnavailableCacheProvider') == UnavailableCacheProviderPCP
    _pot_cache_providers.value.pop('UnavailableCacheProvider')


def test_register_cache_provider_spec(ie):

    @cache.register_spec
    class UnavailableCacheProviderPCSP(PoTokenCacheSpecProvider):
        def is_available(self) -> bool:
            return False

        def generate_cache_spec(self, request: PoTokenRequest):
            return None

    assert _pot_pcs_providers.value.get('UnavailableCacheProvider') == UnavailableCacheProviderPCSP
    _pot_pcs_providers.value.pop('UnavailableCacheProvider')


def test_register_cache_provider_preference(ie):
    before = len(_pot_cache_provider_preferences.value)

    @cache.register_preference(ExampleCacheProviderPCP)
    def unavailable_preference(provider: PoTokenCacheProvider, request: PoTokenRequest):
        return 1

    assert len(_pot_cache_provider_preferences.value) == before + 1


def test_logger_log_level(logger):
    assert logger.LogLevel('INFO') == logger.LogLevel.INFO
    assert logger.LogLevel('debuG') == logger.LogLevel.DEBUG
    assert logger.LogLevel(10) == logger.LogLevel.DEBUG
    assert logger.LogLevel('UNKNOWN') == logger.LogLevel.INFO
