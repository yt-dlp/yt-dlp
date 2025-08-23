from __future__ import annotations

import typing
from collections.abc import Iterable

from yt_dlp.extractor.youtube.js._registry import (
    _jsc_preferences,
    _jsc_providers,
)
from yt_dlp.extractor.youtube.js.provider import (
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
    from yt_dlp.extractor.youtube.js.provider import Preference as JsChallengePreference


class JsChallengeRequestDirector:

    def __init__(self, logger: IEContentProviderLogger):
        self.providers: dict[str, JsChallengeProvider] = {}
        self.preferences: list[JsChallengePreference] = []
        self.logger = logger

    def register_provider(self, provider: JsChallengeProvider):
        self.providers[provider.PROVIDER_KEY] = provider

    def register_preference(self, preference: JsChallengePreference):
        self.preferences.append(preference)

    def _get_providers(self, request: JsChallengeRequest) -> Iterable[JsChallengeProvider]:
        """Sorts available providers by preference, given a request"""
        preferences = {
            provider: sum(pref(provider, request) for pref in self.preferences)
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

    def solve_challenge(self, request: JsChallengeRequest) -> JsChallengeResponse | None:
        if not self.providers:
            self.logger.trace('No JS Challenge providers registered')
            return None

        for provider in self._get_providers(request):
            try:
                self.logger.trace(
                    f'Attempting to solve {request.type.value} JS Challenge from "{provider.PROVIDER_NAME}" provider')
                response = provider.solve(request.copy())
            except JsChallengeProviderRejectedRequest as e:
                self.logger.trace(
                    f'JS Challenge Provider "{provider.PROVIDER_NAME}" rejected this request, '
                    f'trying next available provider. Reason: {e}')
                continue
            except JsChallengeProviderError as e:
                self.logger.warning(
                    f'Error solving {request.type.value} JS Challenge from "{provider.PROVIDER_NAME}" provider: '
                    f'{e!r}{provider_bug_report_message(provider) if not e.expected else ""}')
                continue
            except Exception as e:
                self.logger.error(
                    f'Unexpected error when solving {request.type.value} JS Challenge from "{provider.PROVIDER_NAME}" provider: '
                    f'{e!r}{provider_bug_report_message(provider)}')
                continue

            self.logger.trace(f'JS Challenge response from "{provider.PROVIDER_NAME}" provider: {response}')

            if not validate_response(response):
                self.logger.error(
                    f'Invalid JS Challenge response received from "{provider.PROVIDER_NAME}" provider: '
                    f'{response}{provider_bug_report_message(provider)}')
                continue

            return response

        self.logger.trace(f'No JS Challenge providers were able to solve the {request.type.value} JS Challenge')
        return None

    def close(self):
        for provider in self.providers.values():
            provider.close()


EXTRACTOR_ARG_PREFIX = 'youtubejs'


def initialize_jsc_director(ie):
    assert ie._downloader is not None, 'Downloader not set'

    enable_trace = ie._configuration_arg(
        'js_trace', ['false'], ie_key='youtube', casesense=False)[0] == 'true'

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
        logger=YoutubeIEContentProviderLogger(ie, 'js', log_level=log_level),
    )

    ie._downloader.add_close_hook(director.close)

    for provider in _jsc_providers.value.values():
        logger, settings = get_provider_logger_and_settings(provider, 'js')
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
