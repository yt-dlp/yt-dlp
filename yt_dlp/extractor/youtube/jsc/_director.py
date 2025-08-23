from __future__ import annotations

import typing
from collections.abc import Iterable

from yt_dlp.extractor.youtube.jsc._registry import (
    _jsc_preferences,
    _jsc_providers,
)
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeProviderRejectedRequest,
    JsChallengeRequest,
    JsChallengeResponse,
)
from yt_dlp.extractor.youtube.pot._director import YoutubeIEContentProviderLogger, provider_display_list
from yt_dlp.extractor.youtube.pot._provider import (
    IEContentProviderLogger,
)
from yt_dlp.extractor.youtube.pot.provider import (
    provider_bug_report_message,
)

if typing.TYPE_CHECKING:
    from yt_dlp.extractor.youtube.jsc.provider import Preference as JsChallengePreference


class JsChallengeRequestDirector:

    def __init__(self, logger: IEContentProviderLogger):
        self.providers: dict[str, JsChallengeProvider] = {}
        self.preferences: list[JsChallengePreference] = []
        self.logger = logger

    def register_provider(self, provider: JsChallengeProvider):
        self.providers[provider.PROVIDER_KEY] = provider

    def register_preference(self, preference: JsChallengePreference):
        self.preferences.append(preference)

    def _get_providers(self, requests: list[JsChallengeRequest]) -> Iterable[JsChallengeProvider]:
        """Sorts available providers by preference, given a request"""
        preferences = {
            provider: sum(pref(provider, requests) for pref in self.preferences)
            for provider in self.providers.values()
        }
        if self.logger.log_level <= self.logger.LogLevel.TRACE:
            # calling is_available() for every JS Challenge provider upfront may have some overhead
            self.logger.trace(f'JS Challenge Providers: {provider_display_list(self.providers.values())}')
            self.logger.trace('JS Challenge Provider preferences for this request: {}'.format(', '.join(
                f'{provider.PROVIDER_NAME}={pref}' for provider, pref in preferences.items())))

        return (
            provider for provider in sorted(
                self.providers.values(), key=preferences.get, reverse=True)
            if provider.is_available()
        )

    def bulk_solve(self, requests: list[JsChallengeRequest]) -> list[JsChallengeResponse]:
        """Solves multiple JS Challenges in bulk, returning a list of responses"""
        if not self.providers:
            self.logger.trace('No JS Challenge providers registered')
            return []

        results = []

        next_requests = requests

        for provider in self._get_providers(next_requests):
            next_requests = []

            self.logger.trace(
                f'Attempting to solve {len(requests)} challenges using "{provider.PROVIDER_NAME}" provider')
            responses = provider.bulk_solve([request.copy() for request in requests])
            if len(responses) != len(requests):
                self.logger.warning(
                    f'JS Challenge Provider "{provider.PROVIDER_NAME}" returned {len(responses)} responses for {len(requests)} requests, '
                    f'expected {len(requests)} responses{provider_bug_report_message(provider)}')

            for response in responses:
                if response.error:
                    try:
                        raise response.error
                    except JsChallengeProviderRejectedRequest:
                        # TODO: better error message
                        self.logger.trace(
                            f'JS Challenge Provider "{provider.PROVIDER_NAME}" rejected this request, '
                            f'trying next available provider. Reason: {response.error}, Request: {response.request}')
                        next_requests.append(response.request)
                        continue
                    except JsChallengeProviderError as e:
                        # TODO: better error message
                        self.logger.warning(
                            f'Error solving {response.request.type.value} JS Challenge from "{provider.PROVIDER_NAME}" provider: '
                            f'{e!r}{provider_bug_report_message(provider) if not e.expected else ""}', once=True)
                        next_requests.append(response.request)
                        continue
                    except Exception as e:
                        self.logger.error(
                            f'Unexpected error when solving {response.request.type.value} JS Challenge from "{provider.PROVIDER_NAME}" provider: '
                            f'{e!r}{provider_bug_report_message(provider)}')
                        next_requests.append(response.request)
                        continue

                if not validate_response(response.response):
                    self.logger.error(
                        f'Invalid JS Challenge response received from "{provider.PROVIDER_NAME}" provider: '
                        f'{response.response}{provider_bug_report_message(provider)}')
                    next_requests.append(response.request)
                    continue

                self.logger.trace(f'JS Challenge response from "{provider.PROVIDER_NAME}" provider: {response.response}')
                results.append(response.response)

        if len(results) != len(requests):
            self.logger.trace(
                f'Not all JS Challenges were solved, expected {len(requests)} responses, got {len(results)}')
            self.logger.trace(f'Unsolved requests: {next_requests}')
        else:
            self.logger.trace(f'All {len(requests)} JS Challenges solved successfully')
        return results

    def solve(self, request: JsChallengeRequest) -> JsChallengeResponse | None:
        responses = self.bulk_solve([request])
        return responses[0] if responses else None

    def close(self):
        for provider in self.providers.values():
            provider.close()


EXTRACTOR_ARG_PREFIX = 'youtubejsc'


def initialize_jsc_director(ie):
    assert ie._downloader is not None, 'Downloader not set'

    enable_trace = ie._configuration_arg(
        'jsc_trace', ['false'], ie_key='youtube', casesense=False)[0] == 'true'

    if enable_trace:
        log_level = IEContentProviderLogger.LogLevel.TRACE
    elif ie.get_param('verbose', False):
        log_level = IEContentProviderLogger.LogLevel.DEBUG
    else:
        log_level = IEContentProviderLogger.LogLevel.INFO

    def get_provider_logger_and_settings(provider, logger_key):
        logger_prefix = f'{logger_key}:{provider.PROVIDER_NAME}'
        extractor_key = f'{EXTRACTOR_ARG_PREFIX}-{provider.PROVIDER_KEY.lower()}'
        return (
            YoutubeIEContentProviderLogger(ie, logger_prefix, log_level=log_level),
            ie.get_param('extractor_args', {}).get(extractor_key, {}))

    director = JsChallengeRequestDirector(
        logger=YoutubeIEContentProviderLogger(ie, 'jsc', log_level=log_level),
    )

    ie._downloader.add_close_hook(director.close)

    for provider in _jsc_providers.value.values():
        logger, settings = get_provider_logger_and_settings(provider, 'jsc')
        director.register_provider(provider(ie, logger, settings))

    for preference in _jsc_preferences.value:
        director.register_preference(preference)

    if director.logger.log_level <= director.logger.LogLevel.DEBUG:
        # calling is_available() for every JS Challenge provider upfront may have some overhead
        director.logger.debug(f'JS Challenge Providers: {provider_display_list(director.providers.values())}')
        director.logger.trace(f'Registered {len(director.preferences)} JS Challenge provider preferences')

    return director


def validate_response(response: JsChallengeResponse | None):
    return (
        isinstance(response, JsChallengeResponse)
        and isinstance(response.challenge_result, str)
    )
