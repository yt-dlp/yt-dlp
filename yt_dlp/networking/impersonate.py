from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any, Optional

from .common import RequestHandler, register_preference
from .exceptions import UnsupportedRequest
from ..compat.types import NoneType
from ..utils import classproperty
from ..utils.networking import std_headers


@dataclass(order=True)
class ImpersonateTarget:
    """
    A target for browser impersonation.

    Parameters:
    @param client: the client to impersonate
    @param version: the client version to impersonate
    @param os: the client OS to impersonate
    @param os_vers: the client OS version to impersonate

    Note: None is used to indicate to match any.
    """
    client: Optional[str] = None
    version: Optional[str] = None
    os: Optional[str] = None
    os_vers: Optional[str] = None

    def __contains__(self, target: ImpersonateTarget):
        if not isinstance(target, ImpersonateTarget):
            return False
        return (
            (self.client is None or target.client is None or self.client == target.client)
            and (self.version is None or target.version is None or self.version == target.version)
            and (self.os is None or target.os is None or self.os == target.os)
            and (self.os_vers is None or target.os_vers is None or self.os_vers == target.os_vers)
        )

    def __str__(self):
        filtered_parts = [
            str(part) if part is not None else ''
            for part in (self.client, self.version, self.os, self.os_vers)
        ]
        return ':'.join(filtered_parts).rstrip(':')

    @classmethod
    def from_str(cls, target: str):
        return ImpersonateTarget(*[
            None if (v or '').strip() == '' else v for v in target.split(':')
        ])

    def __hash__(self):
        return hash((self.client, self.version, self.os, self.os_vers))


class ImpersonateRequestHandler(RequestHandler, ABC):
    """
    Base class for request handlers that support browser impersonation.

    This provides a method for checking the validity of the impersonate extension,
    which can be used in _check_extensions.

    Impersonate targets consist of a client, version, os and os_vers.
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
    def supported_targets(self) -> tuple[ImpersonateTarget]:
        return tuple(self._SUPPORTED_IMPERSONATE_TARGET_MAP.keys())

    def is_supported_target(self, target: ImpersonateTarget):
        assert isinstance(target, ImpersonateTarget)
        return self._resolve_target(target) is not None

    def _get_request_target(self, request):
        """Get the requested target for the request"""
        return request.extensions.get('impersonate') or self.impersonate

    def _get_mapped_request_target(self, request):
        """Get the resolved mapped target for the request target"""
        resolved_target = self._resolve_target(self._get_request_target(request))
        return self._SUPPORTED_IMPERSONATE_TARGET_MAP.get(
            resolved_target, None)

    def _get_impersonate_headers(self, request):
        headers = self._merge_headers(request.headers)
        if self._get_request_target(request) is not None:
            # remove all headers present in std_headers
            headers.pop('User-Agent', None)
            for header in std_headers:
                if header in headers and std_headers[header] == headers[header]:
                    headers.pop(header, None)
        return headers


@register_preference(ImpersonateRequestHandler)
def impersonate_preference(rh, request):
    if request.extensions.get('impersonate') is not None or rh.impersonate is not None:
        return 1000
    return 0
