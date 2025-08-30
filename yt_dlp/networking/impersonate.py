from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass
from typing import Any

from .common import RequestHandler, register_preference, Request
from .exceptions import UnsupportedRequest
from ..compat.types import NoneType
from ..utils import classproperty, join_nonempty
from ..utils.networking import std_headers, HTTPHeaderDict


@dataclass(order=True, frozen=True)
class ImpersonateTarget:
    """
    A target for browser impersonation.

    Parameters:
    @param client: the client to impersonate
    @param version: the client version to impersonate
    @param os: the client OS to impersonate
    @param os_version: the client OS version to impersonate

    Note: None is used to indicate to match any.

    """
    client: str | None = None
    version: str | None = None
    os: str | None = None
    os_version: str | None = None

    def __post_init__(self):
        if self.version and not self.client:
            raise ValueError('client is required if version is set')
        if self.os_version and not self.os:
            raise ValueError('os is required if os_version is set')

    def __contains__(self, target: ImpersonateTarget):
        if not isinstance(target, ImpersonateTarget):
            return False
        return (
            (self.client is None or target.client is None or self.client == target.client)
            and (self.version is None or target.version is None or self.version == target.version)
            and (self.os is None or target.os is None or self.os == target.os)
            and (self.os_version is None or target.os_version is None or self.os_version == target.os_version)
        )

    def __str__(self):
        return f'{join_nonempty(self.client, self.version)}:{join_nonempty(self.os, self.os_version)}'.rstrip(':')

    @classmethod
    def from_str(cls, target: str):
        mobj = re.fullmatch(r'(?:(?P<client>[^:-]+)(?:-(?P<version>[^:-]+))?)?(?::(?:(?P<os>[^:-]+)(?:-(?P<os_version>[^:-]+))?)?)?', target)
        if not mobj:
            raise ValueError(f'Invalid impersonate target "{target}"')
        return cls(**mobj.groupdict())


class ImpersonateRequestHandler(RequestHandler, ABC):
    """
    Base class for request handlers that support browser impersonation.

    This provides a method for checking the validity of the impersonate extension,
    which can be used in _check_extensions.

    Impersonate targets consist of a client, version, os and os_ver.
    See the ImpersonateTarget class for more details.

    The following may be defined:
     - `_SUPPORTED_IMPERSONATE_TARGET_MAP`: a dict mapping supported targets to custom object.
                Any Request with an impersonate target not in this list will raise an UnsupportedRequest.
                Set to None to disable this check.
                Note: Entries are in order of preference

    Parameters:
    @param impersonate: the default impersonate target to use for requests.
                        Set to None to disable impersonation.
    """
    _SUPPORTED_IMPERSONATE_TARGET_MAP: dict[ImpersonateTarget, Any] = {}

    def __init__(self, *, impersonate: ImpersonateTarget = None, **kwargs):
        super().__init__(**kwargs)
        self.impersonate = impersonate

    def _check_impersonate_target(self, target: ImpersonateTarget):
        assert isinstance(target, (ImpersonateTarget, NoneType))
        if target is None or not self.supported_targets:
            return
        if not self.is_supported_target(target):
            raise UnsupportedRequest(f'Unsupported impersonate target: {target}')

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        if 'impersonate' in extensions:
            self._check_impersonate_target(extensions.get('impersonate'))

    def _validate(self, request):
        super()._validate(request)
        self._check_impersonate_target(self.impersonate)

    def _resolve_target(self, target: ImpersonateTarget | None):
        """Resolve a target to a supported target."""
        if target is None:
            return
        for supported_target in self.supported_targets:
            if target in supported_target:
                if self.verbose:
                    self._logger.stdout(
                        f'{self.RH_NAME}: resolved impersonate target {target} to {supported_target}')
                return supported_target

    @classproperty
    def supported_targets(cls) -> tuple[ImpersonateTarget, ...]:
        return tuple(cls._SUPPORTED_IMPERSONATE_TARGET_MAP.keys())

    def is_supported_target(self, target: ImpersonateTarget):
        assert isinstance(target, ImpersonateTarget)
        return self._resolve_target(target) is not None

    def _get_request_target(self, request):
        """Get the requested target for the request"""
        return self._resolve_target(request.extensions.get('impersonate') or self.impersonate)

    def _prepare_impersonate_headers(self, request: Request, headers: HTTPHeaderDict) -> None:  # noqa: B027
        """Additional operations to prepare headers before building. To be extended by subclasses.
        @param request: Request object
        @param headers: Merged headers to prepare
        """

    def _get_impersonate_headers(self, request: Request) -> dict[str, str]:
        """
        Get headers for external impersonation use.
        Subclasses may define a _prepare_impersonate_headers method to modify headers after merge but before building.
        """
        headers = self._merge_headers(request.headers)
        if self._get_request_target(request) is not None:
            # remove all headers present in std_headers
            # TODO: change this to not depend on std_headers
            for k, v in std_headers.items():
                if headers.get(k) == v:
                    headers.pop(k)

        self._prepare_impersonate_headers(request, headers)
        if request.extensions.get('keep_header_casing'):
            return headers.sensitive()
        return dict(headers)


@register_preference(ImpersonateRequestHandler)
def impersonate_preference(rh, request):
    if request.extensions.get('impersonate') or rh.impersonate:
        return 1000
    return 0
