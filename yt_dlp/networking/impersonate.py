from __future__ import annotations

from abc import ABC
from typing import Any, Optional, Tuple

from .common import RequestHandler, register_preference
from .exceptions import UnsupportedRequest
from ..compat.types import NoneType
from ..utils.networking import std_headers

ImpersonateTarget = Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]


def _target_within(target1: ImpersonateTarget, target2: ImpersonateTarget):
    for i in range(0, min(len(target1), len(target2))):
        if (
            target1[i]
            and target2[i]
            and target1[i] != target2[i]
        ):
            return False

    return True


class ImpersonateRequestHandler(RequestHandler, ABC):
    """
    Base class for request handlers that support browser impersonation.

    This provides a method for checking the validity of the impersonate extension,
    which can be used in _check_extensions.

    Impersonate targets are defined as a tuple of (client, version, os, os_vers).
    Note: Impersonate targets are not required to define all fields (except client).

    The following may be defined:
     - `_SUPPORTED_IMPERSONATE_TARGET_TUPLES`: a tuple of supported targets to impersonate.
        Any Request with an impersonate target not in this list will raise an UnsupportedRequest.
        Set to None to disable this check.
     - `_SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP`: a dict mapping supported targets to custom targets.
        This works similar to `_SUPPORTED_IMPERSONATE_TARGET_TUPLES`.

    Note: Only one of `_SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP` and `_SUPPORTED_IMPERSONATE_TARGET_TUPLES` can be defined.
    Note: Entries are in order of preference

    Parameters:
    @param impersonate: the default impersonate target to use for requests.
                        Set to None to disable impersonation.
    """
    _SUPPORTED_IMPERSONATE_TARGET_TUPLES: tuple[ImpersonateTarget] = ()
    _SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP: dict[ImpersonateTarget, Any] = {}

    def __init__(self, *, impersonate: ImpersonateTarget = None, **kwargs):
        super().__init__(**kwargs)
        self.impersonate = impersonate

    def _check_impersonate_target(self, target: ImpersonateTarget):
        assert isinstance(target, (tuple, NoneType))
        if target is None or not self.get_supported_targets():
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
        for supported_target in self.get_supported_targets():
            if _target_within(target, supported_target):
                if self.verbose:
                    self._logger.stdout(
                        f'{self.RH_NAME}: resolved impersonate target {target} to {supported_target}')
                return supported_target

    def get_supported_targets(self) -> tuple[ImpersonateTarget]:
        return tuple(self._SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP.keys()) or tuple(self._SUPPORTED_IMPERSONATE_TARGET_TUPLES)

    def is_supported_target(self, target: ImpersonateTarget):
        return self._resolve_target(target) is not None

    def _get_request_target(self, request):
        """Get the requested target for the request"""
        return request.extensions.get('impersonate') or self.impersonate

    def _get_resolved_request_target(self, request) -> ImpersonateTarget:
        """Get the resolved target for this request. This gives the matching supported target"""
        return self._resolve_target(self._get_request_target(request))

    def _get_mapped_request_target(self, request):
        """Get the resolved mapped target for the request target"""
        resolved_target = self._resolve_target(self._get_request_target(request))
        return self._SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP.get(
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
