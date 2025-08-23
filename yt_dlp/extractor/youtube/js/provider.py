"""PUBLIC API"""

from __future__ import annotations

import abc
import dataclasses
import enum
import typing

from yt_dlp.extractor.youtube.js._registry import _jsc_preferences, _jsc_providers
from yt_dlp.extractor.youtube.pot._provider import (
    IEContentProvider,
    IEContentProviderError,
    register_preference_generic,
    register_provider_generic,
)
from yt_dlp.utils import ExtractorError

__all__ = [
    'JsChallengeProvider',
    'JsChallengeProviderError',
    'JsChallengeProviderRejectedRequest',
    'JsChallengeRequest',
    'JsChallengeResponse',
    'JsChallengeType',
    'register_preference',
    'register_provider',
]


class JsChallengeType(enum.Enum):
    NSIG = 'nsig'
    SIG = 'sig'


@dataclasses.dataclass
class JsChallengeRequest:
    type: JsChallengeType
    challenge: str
    player_url: str | None = None
    video_id: str | None = None

    def copy(self):
        return dataclasses.replace(self)


@dataclasses.dataclass
class JsChallengeResponse:
    challenge_result: str


class JsChallengeProviderRejectedRequest(IEContentProviderError):
    """Reject the JsChallengeRequest (cannot handle the request)"""


class JsChallengeProviderError(IEContentProviderError):
    """An error occurred while solving the challenge"""


class JsChallengeProvider(IEContentProvider, abc.ABC, suffix='JCP'):

    # Set to None to disable the check
    _SUPPORTED_TYPES: tuple[JsChallengeType] | None = ()

    def __validate_request(self, request: JsChallengeRequest):
        if not self.is_available():
            raise JsChallengeProviderRejectedRequest(f'{self.PROVIDER_NAME} is not available')

        # Validate request using built-in settings
        if (
            self._SUPPORTED_TYPES is not None
            and request.type not in self._SUPPORTED_TYPES
        ):
            raise JsChallengeProviderRejectedRequest(
                f'JS Challenge type "{request.type}" is not supported by {self.PROVIDER_NAME}')

    def solve(self, request: JsChallengeRequest) -> JsChallengeResponse:
        """Solve the JS challenge and return the result"""
        self.__validate_request(request)
        return self._real_solve(request)

    def request_pot(self, request: JsChallengeRequest) -> JsChallengeResponse:
        self.__validate_request(request)
        return self._real_solve(request)

    @abc.abstractmethod
    def _real_solve(self, request: JsChallengeRequest) -> JsChallengeResponse:
        """To be implemented by subclasses"""
        pass

    def _get_player(self, video_id, player_url):
        try:
            return self.ie._load_player(
                video_id=video_id,
                player_url=player_url,
                fatal=True,
            )
        except ExtractorError as e:
            raise JsChallengeProviderError(
                f'Failed to load player for JS challenge: {e}') from e


def register_provider(provider: type[JsChallengeProvider]):
    """Register a JsChallengeProvider class"""
    return register_provider_generic(
        provider=provider,
        base_class=JsChallengeProvider,
        registry=_jsc_providers.value,
    )


def register_preference(*providers: type[JsChallengeProvider]) -> typing.Callable[[Preference], Preference]:
    """Register a preference for a JsChallengeProvider class."""
    return register_preference_generic(
        JsChallengeProvider,
        _jsc_preferences.value,
        *providers,
    )


if typing.TYPE_CHECKING:
    Preference = typing.Callable[[JsChallengeProvider, JsChallengeRequest], int]
    __all__.append('Preference')
