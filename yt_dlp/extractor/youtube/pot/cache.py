"""PUBLIC API"""

from __future__ import annotations

import abc
import dataclasses
import enum
import typing

from yt_dlp.extractor.youtube.pot._provider import (
    IEContentProvider,
    IEContentProviderError,
    register_preference_generic,
    register_provider_generic,
)
from yt_dlp.extractor.youtube.pot._registry import (
    _pot_cache_provider_preferences,
    _pot_cache_providers,
    _pot_pcs_providers,
)
from yt_dlp.extractor.youtube.pot.provider import PoTokenRequest


class PoTokenCacheProviderError(IEContentProviderError):
    """An error occurred while fetching a PO Token"""


class PoTokenCacheProvider(IEContentProvider, abc.ABC, suffix='PCP'):
    @abc.abstractmethod
    def get(self, key: str) -> str | None:
        pass

    @abc.abstractmethod
    def store(self, key: str, value: str, expires_at: int):
        pass

    @abc.abstractmethod
    def delete(self, key: str):
        pass


class CacheProviderWritePolicy(enum.Enum):
    WRITE_ALL = enum.auto()    # Write to all cache providers
    WRITE_FIRST = enum.auto()  # Write to only the first cache provider


@dataclasses.dataclass
class PoTokenCacheSpec:
    key_bindings: dict[str, str | None]
    default_ttl: int
    write_policy: CacheProviderWritePolicy = CacheProviderWritePolicy.WRITE_ALL

    # Internal
    _provider: PoTokenCacheSpecProvider | None = None


class PoTokenCacheSpecProvider(IEContentProvider, abc.ABC, suffix='PCSP'):

    def is_available(self) -> bool:
        return True

    @abc.abstractmethod
    def generate_cache_spec(self, request: PoTokenRequest) -> PoTokenCacheSpec | None:
        """Generate a cache spec for the given request"""
        pass


def register_provider(provider: type[PoTokenCacheProvider]):
    """Register a PoTokenCacheProvider class"""
    return register_provider_generic(
        provider=provider,
        base_class=PoTokenCacheProvider,
        registry=_pot_cache_providers.value,
    )


def register_spec(provider: type[PoTokenCacheSpecProvider]):
    """Register a PoTokenCacheSpecProvider class"""
    return register_provider_generic(
        provider=provider,
        base_class=PoTokenCacheSpecProvider,
        registry=_pot_pcs_providers.value,
    )


def register_preference(
        *providers: type[PoTokenCacheProvider]) -> typing.Callable[[CacheProviderPreference], CacheProviderPreference]:
    """Register a preference for a PoTokenCacheProvider"""
    return register_preference_generic(
        PoTokenCacheProvider,
        _pot_cache_provider_preferences.value,
        *providers,
    )


if typing.TYPE_CHECKING:
    CacheProviderPreference = typing.Callable[[PoTokenCacheProvider, PoTokenRequest], int]
