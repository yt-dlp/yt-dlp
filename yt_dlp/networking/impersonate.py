from __future__ import annotations
from abc import ABC
from typing import Optional, Any

from .common import RequestHandler, register_preference
from .exceptions import UnsupportedRequest
from ..compat.types import NoneType
from ..utils.networking import std_headers


ImpersonateTarget = tuple[Optional[str], Optional[str], Optional[str], Optional[str]]


def parse_impersonate_target(target: str) -> ImpersonateTarget:
    client = version = os = os_vers = None
    if not target:
        return client, version, os, os_vers
    parts = target.split(':')
    if len(parts):
        client = parts[0]
    if len(parts) > 1:
        version = parts[1]
    if len(parts) > 2:
        os = parts[2]
        if len(parts) > 3:
            os_vers = parts[3]

    return client, version, os, os_vers


def compile_impersonate_target(browser, version, os, os_vers) -> str:
    target = browser
    if version:
        target += ':' + version
    if os:
        if not version:
            target += ':'
        target += ':' + os
        if os_vers:
            target += ':' + os_vers
    return target


def target_within(target1: ImpersonateTarget, target2: ImpersonateTarget):
    # required: check if the browser matches
    if target1[0] != target2[0]:
        return False

    for i in range(1, len(target2)):
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

    Impersonate target tuples are defined as a tuple of (browser, version, os, os_vers) internally.
    To simplify the interface, this is compiled into a string format of browser:version:os:os_vers to be used externally.
    - In this handler, "impersonate target tuple" refers to the tuple version,
      and "impersonate target" refers to the string version.
    - Impersonate target [tuples] are not required to define all fields (except browser).

    The following may be defined:
     - `_SUPPORTED_IMPERSONATE_TARGET_TUPLES`: a tuple of supported target tuples to impersonate.
        Any Request with an impersonate target not in this list will raise an UnsupportedRequest.
        Set to None to disable this check.
     - `_SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP`: a dict mapping supported target tuples to custom targets.
        This works similar to `_SUPPORTED_IMPERSONATE_TARGET_TUPLES`.

    Note: Only one of `_SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP` and `_SUPPORTED_IMPERSONATE_TARGET_TUPLES` can be defined.
    Note: Entries are in order of preference

    Parameters:
    @param impersonate: the default impersonate target to use for requests.
                        Set to None to disable impersonation.
    """
    _SUPPORTED_IMPERSONATE_TARGET_TUPLES: tuple[ImpersonateTarget] = ()
    _SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP: dict[ImpersonateTarget, Any] = {}

    def __init__(self, *, impersonate=None, **kwargs):
        super().__init__(**kwargs)
        self.impersonate = impersonate

    def _check_impersonate_target(self, target: str):
        assert isinstance(target, (str, NoneType))
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

    def _get_supported_target_tuples(self):
        return tuple(self._SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP.keys()) or tuple(self._SUPPORTED_IMPERSONATE_TARGET_TUPLES)

    def _resolve_target_tuple(self, target: ImpersonateTarget | None):
        """Resolve a target to a supported target."""
        if not target:
            return
        for supported_target in self._get_supported_target_tuples():
            if target_within(target, supported_target):
                if self.verbose:
                    self._logger.stdout(
                        f'{self.RH_NAME}: resolved impersonate target "{compile_impersonate_target(*target)}" '
                        f'to "{compile_impersonate_target(*supported_target)}"')
                return supported_target

    def get_supported_targets(self) -> tuple[str]:
        return tuple(compile_impersonate_target(*target) for target in self._get_supported_target_tuples())

    def is_supported_target(self, target: str):
        return self._is_supported_target_tuple(parse_impersonate_target(target))

    def _is_supported_target_tuple(self, target: ImpersonateTarget):
        return self._resolve_target_tuple(target) is not None

    def _get_target_tuple(self, request):
        """Get the requested target tuple for the request"""
        target = request.extensions.get('impersonate') or self.impersonate
        if target:
            return parse_impersonate_target(target)

    def _get_resolved_target_tuple(self, request) -> ImpersonateTarget:
        """Get the resolved target tuple for this request. This gives the matching supported target"""
        return self._resolve_target_tuple(self._get_target_tuple(request))

    def _get_mapped_target(self, request):
        """Get the resolved mapped target for the request target"""
        resolved_target = self._resolve_target_tuple(self._get_target_tuple(request))
        return self._SUPPORTED_IMPERSONATE_TARGET_TUPLE_MAP.get(
            resolved_target, None)

    def _get_impersonate_headers(self, request):
        headers = self._merge_headers(request.headers)
        if self._get_target_tuple(request):
            # remove all headers present in std_headers
            headers.pop('User-Agent', None)
            for header in std_headers:
                if header in headers and std_headers[header] == headers[header]:
                    headers.pop(header, None)
        return headers


@register_preference(ImpersonateRequestHandler)
def impersonate_preference(rh, request):
    if request.extensions.get('impersonate') or rh.impersonate:
        return 1000
    return 0


def get_available_impersonate_targets(director):
    return director.collect_from_handlers(
        lambda x: x.get_supported_targets(),
        [lambda _, v: isinstance(v, ImpersonateRequestHandler)]
    )
