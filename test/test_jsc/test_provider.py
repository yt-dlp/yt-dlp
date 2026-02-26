
import pytest

from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeRequest,
    JsChallengeProviderResponse,
    JsChallengeProviderRejectedRequest,
    JsChallengeType,
    JsChallengeResponse,
    NChallengeOutput,
    NChallengeInput,
    JsChallengeProviderError,
    register_provider,
    register_preference,
)
from yt_dlp.extractor.youtube.pot._provider import IEContentProvider
from yt_dlp.utils import ExtractorError
from yt_dlp.extractor.youtube.jsc._registry import _jsc_preferences, _jsc_providers


class ExampleJCP(JsChallengeProvider):
    PROVIDER_NAME = 'example-provider'
    PROVIDER_VERSION = '0.0.1'
    BUG_REPORT_LOCATION = 'https://example.com/issues'

    _SUPPORTED_TYPES = [JsChallengeType.N]

    def is_available(self) -> bool:
        return True

    def _real_bulk_solve(self, requests):
        for request in requests:
            results = dict.fromkeys(request.input.challenges, 'example-solution')
            response = JsChallengeResponse(
                type=request.type,
                output=NChallengeOutput(results=results))
            yield JsChallengeProviderResponse(request=request, response=response)


PLAYER_URL = 'https://example.com/player.js'


class TestJsChallengeProvider:
    # note: some test covered in TestPoTokenProvider which shares the same base class
    def test_base_type(self):
        assert issubclass(JsChallengeProvider, IEContentProvider)

    def test_create_provider_missing_bulk_solve_method(self, ie, logger):
        class MissingMethodsJCP(JsChallengeProvider):
            def is_available(self) -> bool:
                return True

        with pytest.raises(TypeError, match='bulk_solve'):
            MissingMethodsJCP(ie=ie, logger=logger, settings={})

    def test_create_provider_missing_available_method(self, ie, logger):
        class MissingMethodsJCP(JsChallengeProvider):
            def _real_bulk_solve(self, requests):
                raise JsChallengeProviderRejectedRequest('Not implemented')

        with pytest.raises(TypeError, match='is_available'):
            MissingMethodsJCP(ie=ie, logger=logger, settings={})

    def test_barebones_provider(self, ie, logger):
        class BarebonesProviderJCP(JsChallengeProvider):
            def is_available(self) -> bool:
                return True

            def _real_bulk_solve(self, requests):
                raise JsChallengeProviderRejectedRequest('Not implemented')

        provider = BarebonesProviderJCP(ie=ie, logger=logger, settings={})
        assert provider.PROVIDER_NAME == 'BarebonesProvider'
        assert provider.PROVIDER_KEY == 'BarebonesProvider'
        assert provider.PROVIDER_VERSION == '0.0.0'
        assert provider.BUG_REPORT_MESSAGE == 'please report this issue to the provider developer at  (developer has not provided a bug report location)  .'

    def test_example_provider_success(self, ie, logger):
        provider = ExampleJCP(ie=ie, logger=logger, settings={})

        request = JsChallengeRequest(
            type=JsChallengeType.N,
            input=NChallengeInput(player_url=PLAYER_URL, challenges=['example-challenge']))

        request_two = JsChallengeRequest(
            type=JsChallengeType.N,
            input=NChallengeInput(player_url=PLAYER_URL, challenges=['example-challenge-2']))

        responses = list(provider.bulk_solve([request, request_two]))
        assert len(responses) == 2
        assert all(isinstance(r, JsChallengeProviderResponse) for r in responses)
        assert responses == [
            JsChallengeProviderResponse(
                request=request,
                response=JsChallengeResponse(
                    type=JsChallengeType.N,
                    output=NChallengeOutput(results={'example-challenge': 'example-solution'}),
                ),
            ),
            JsChallengeProviderResponse(
                request=request_two,
                response=JsChallengeResponse(
                    type=JsChallengeType.N,
                    output=NChallengeOutput(results={'example-challenge-2': 'example-solution'}),
                ),
            ),
        ]

    def test_provider_unsupported_challenge_type(self, ie, logger):
        provider = ExampleJCP(ie=ie, logger=logger, settings={})
        request_supported = JsChallengeRequest(
            type=JsChallengeType.N,
            input=NChallengeInput(player_url=PLAYER_URL, challenges=['example-challenge']))
        request_unsupported = JsChallengeRequest(
            type=JsChallengeType.SIG,
            input=NChallengeInput(player_url=PLAYER_URL, challenges=['example-challenge']))
        responses = list(provider.bulk_solve([request_supported, request_unsupported, request_supported]))
        assert len(responses) == 3
        # Requests are validated first before continuing to _real_bulk_solve
        assert isinstance(responses[0], JsChallengeProviderResponse)
        assert isinstance(responses[0].error, JsChallengeProviderRejectedRequest)
        assert responses[0].request is request_unsupported
        assert str(responses[0].error) == 'JS Challenge type "JsChallengeType.SIG" is not supported by example-provider'

        assert responses[1:] == [
            JsChallengeProviderResponse(
                request=request_supported,
                response=JsChallengeResponse(
                    type=JsChallengeType.N,
                    output=NChallengeOutput(results={'example-challenge': 'example-solution'}),
                ),
            ),
            JsChallengeProviderResponse(
                request=request_supported,
                response=JsChallengeResponse(
                    type=JsChallengeType.N,
                    output=NChallengeOutput(results={'example-challenge': 'example-solution'}),
                ),
            ),
        ]

    def test_provider_get_player(self, ie, logger):
        ie._load_player = lambda video_id, player_url, fatal: (video_id, player_url, fatal)
        provider = ExampleJCP(ie=ie, logger=logger, settings={})
        assert provider._get_player('video123', PLAYER_URL) == ('video123', PLAYER_URL, True)

    def test_provider_get_player_error(self, ie, logger):
        def raise_error(video_id, player_url, fatal):
            raise ExtractorError('Failed to load player')

        ie._load_player = raise_error
        provider = ExampleJCP(ie=ie, logger=logger, settings={})
        with pytest.raises(JsChallengeProviderError, match='Failed to load player for JS challenge'):
            provider._get_player('video123', PLAYER_URL)

    def test_require_class_end_with_suffix(self, ie, logger):
        class InvalidSuffix(JsChallengeProvider):
            PROVIDER_NAME = 'invalid-suffix'

            def _real_bulk_solve(self, requests):
                raise JsChallengeProviderRejectedRequest('Not implemented')

            def is_available(self) -> bool:
                return True

        provider = InvalidSuffix(ie=ie, logger=logger, settings={})

        with pytest.raises(AssertionError):
            provider.PROVIDER_KEY  # noqa: B018


def test_register_provider(ie):

    @register_provider
    class UnavailableProviderJCP(JsChallengeProvider):
        def is_available(self) -> bool:
            return False

        def _real_bulk_solve(self, requests):
            raise JsChallengeProviderRejectedRequest('Not implemented')

    assert _jsc_providers.value.get('UnavailableProvider') == UnavailableProviderJCP
    _jsc_providers.value.pop('UnavailableProvider')


def test_register_preference(ie):
    before = len(_jsc_preferences.value)

    @register_preference(ExampleJCP)
    def unavailable_preference(*args, **kwargs):
        return 1

    assert len(_jsc_preferences.value) == before + 1
