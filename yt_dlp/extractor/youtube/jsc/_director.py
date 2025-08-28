from __future__ import annotations

import dataclasses
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
    JsChallengeType,
    NSigChallengeInput,
    NSigChallengeOutput,
    SigChallengeInput,
    SigChallengeOutput,
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

    def _handle_error(self, e: Exception, provider: JsChallengeProvider, requests: list[JsChallengeRequest]):
        # xxx: this seems kinda jank
        # TODO: add useful debugging information (e.g. request details)
        if isinstance(e, JsChallengeProviderRejectedRequest):
            self.logger.trace(
                f'JS Challenge Provider "{provider.PROVIDER_NAME}" rejected '
                f'{"this request" if len(requests) == 1 else f"{len(requests)} requests"}, '
                f'trying next available provider. Reason: {e}'
                + (f', Request: {getattr(e, "request", None)}' if hasattr(e, 'request') else ''),
            )
        elif isinstance(e, JsChallengeProviderError):
            self.logger.warning(
                f'Error solving {requests[0].type.value if len(requests) == 1 else f"{len(requests)}"} JS Challenge '
                f'from "{provider.PROVIDER_NAME}" provider: {e!r}'
                + (provider_bug_report_message(provider) if not e.expected else ''),
                once=True,
            )
        else:
            self.logger.error(
                f'Unexpected error when solving {requests[0].type.value if len(requests) == 1 else f"{len(requests)}"} JS Challenge '
                f'from "{provider.PROVIDER_NAME}" provider: {e!r}{provider_bug_report_message(provider)}',
            )

    def bulk_solve(self, requests: list[JsChallengeRequest]) -> list[tuple[JsChallengeRequest, JsChallengeResponse]]:
        """Solves multiple JS Challenges in bulk, returning a list of responses"""
        if not self.providers:
            self.logger.trace('No JS Challenge providers registered')
            return []

        results = []
        next_requests = requests[:]

        for provider in self._get_providers(next_requests):
            self.logger.trace(
                f'Attempting to solve {len(next_requests)} challenges using "{provider.PROVIDER_NAME}" provider')
            try:
                for response in provider.bulk_solve([dataclasses.replace(request) for request in next_requests]):
                    if response.error:
                        self._handle_error(response.error, provider, [response.request])
                        continue
                    if not validate_response(response.response, response.request):
                        self.logger.error(
                            f'Invalid JS Challenge response received from "{provider.PROVIDER_NAME}" provider: '
                            f'{response.response}{provider_bug_report_message(provider)}')
                        continue
                    try:
                        next_requests.remove(response.request)
                    except ValueError:
                        self.logger.error(
                            f'JS Challenge Provider "{provider.PROVIDER_NAME}" returned a response for an unknown request: {response.request}'
                            f'{provider_bug_report_message(provider)}')
                        continue
                    results.append((response.request, response.response))
            except Exception as e:
                self._handle_error(e, provider, next_requests)
                continue

        if len(results) != len(requests):
            self.logger.trace(
                f'Not all JS Challenges were solved, expected {len(requests)} responses, got {len(results)}')
            self.logger.trace(f'Unsolved requests: {next_requests}')
        else:
            self.logger.trace(f'Solved all {len(requests)} requested JS Challenges')
        return results

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


def validate_response(response: JsChallengeResponse, request: JsChallengeRequest) -> bool:
    return (
        isinstance(response, JsChallengeResponse)
        and (
            (request.type == JsChallengeType.NSIG and validate_output(response.output, request.input, NSigChallengeOutput))
            or (request.type == JsChallengeType.SIG and validate_output(response.output, request.input, SigChallengeOutput))
        )
    )


def validate_output(
        challenge_output: NSigChallengeOutput | SigChallengeOutput,
        challenge_input: NSigChallengeInput | SigChallengeInput,
        output_class,
) -> bool:
    # Since the two classes have same structure, we can use a single validation function for now
    return (
        isinstance(challenge_output, output_class)
        and len(challenge_output.results) == len(challenge_input.challenges)
        and all(isinstance(k, str) and isinstance(v, str) for k, v in challenge_output.results.items())
        and all(challenge in challenge_output.results for challenge in challenge_input.challenges)
        # Extra validation for SigChallengeOutput specs
        and (output_class != SigChallengeOutput or (
            isinstance(challenge_output.specs, dict)
            and all(
                isinstance(k, str) and isinstance(v, list) and all(isinstance(i, int) for i in v)
                for k, v in challenge_output.specs.items())
        ))
    )
