"""PUBLIC API"""

from __future__ import annotations

import abc
import dataclasses
import enum
import typing

from yt_dlp.extractor.youtube.jsc._registry import _jsc_preferences, _jsc_providers
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
    'JsChallengeProviderResponse',
    'JsChallengeRequest',
    'JsChallengeResponse',
    'JsChallengeType',
    'NChallengeInput',
    'NChallengeOutput',
    'SigChallengeInput',
    'SigChallengeOutput',
    'register_preference',
    'register_provider',
]


class JsChallengeType(enum.Enum):
    N = 'n'
    SIG = 'sig'


@dataclasses.dataclass(frozen=True)
class JsChallengeRequest:
    type: JsChallengeType
    input: NChallengeInput | SigChallengeInput
    video_id: str | None = None


@dataclasses.dataclass(frozen=True)
class NChallengeInput:
    player_url: str
    challenges: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class SigChallengeInput:
    player_url: str
    challenges: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class NChallengeOutput:
    results: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class SigChallengeOutput:
    results: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class JsChallengeProviderResponse:
    request: JsChallengeRequest
    response: JsChallengeResponse | None = None
    error: Exception | None = None


@dataclasses.dataclass
class JsChallengeResponse:
    type: JsChallengeType
    output: NChallengeOutput | SigChallengeOutput


class JsChallengeProviderRejectedRequest(IEContentProviderError):
    """Reject the JsChallengeRequest (cannot handle the request)"""

    def __init__(self, msg=None, expected: bool = False, *, _skipped_components=None):
        super().__init__(msg, expected)
        self._skipped_components = _skipped_components


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

    def bulk_solve(self, requests: list[JsChallengeRequest]) -> typing.Generator[JsChallengeProviderResponse, None, None]:
        """Solve multiple JS challenges and return the results"""
        validated_requests = []
        for request in requests:
            try:
                self.__validate_request(request)
                validated_requests.append(request)
            except JsChallengeProviderRejectedRequest as e:
                yield JsChallengeProviderResponse(request=request, error=e)
                continue
        yield from self._real_bulk_solve(validated_requests)

    @abc.abstractmethod
    def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> typing.Generator[JsChallengeProviderResponse, None, None]:
        """Subclasses can override this method to handle bulk solving"""
        raise NotImplementedError(f'{self.PROVIDER_NAME} does not implement bulk solving')

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
    Preference = typing.Callable[[JsChallengeProvider, list[JsChallengeRequest]], int]
    __all__.append('Preference')
