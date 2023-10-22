from __future__ import annotations
from abc import ABC

from typing import Optional, Any

from .common import RequestHandler, register_preference
from .exceptions import UnsupportedRequest
from ..compat.types import NoneType
from ..utils.networking import std_headers


# client, version, os, os_vers
# chrome:110:win:10
# chrome::win:10

# client[:version][:[:os[:os_vers]]]

# generic syntax: client[:version][:os][:os_vers]

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

    The following may be defined:
     `_SUPPORTED_IMPERSONATE_TARGETS`: a tuple of supported targets to impersonate,
        in compiled target format. Any Request with an impersonate
        target not in this list will raise an UnsupportedRequest.
        Set to None to disable this check.

    Parameters:
    @param impersonate: the default impersonate target to use for requests.
                        Set to None to disable impersonation.
    """
    _SUPPORTED_IMPERSONATE_TARGETS: tuple[ImpersonateTarget] = ()
    _SUPPORTED_IMPERSONATE_TARGET_MAP: dict[ImpersonateTarget, Any] = {}

    def __init__(self, *, impersonate=None, **kwargs):
        super().__init__(**kwargs)
        self.impersonate = impersonate

    def _get_impersonate_target_str(self, request):
        return request.extensions.get('impersonate') or self.impersonate

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        self._check_impersonate_target_str(extensions.get('impersonate'))

    def _get_supported_targets(self):
        return tuple(self._SUPPORTED_IMPERSONATE_TARGET_MAP.keys()) or tuple(self._SUPPORTED_IMPERSONATE_TARGETS)

    # TODO: could probably merge with the resolve target function
    def _is_target_supported(self, target: tuple):
        for supported_target in self._get_supported_targets():
            if target_within(target, supported_target):
                if self.verbose:
                    self._logger.stdout(
                        f'{self.RH_NAME}: resolved impersonate target "{compile_impersonate_target(*target)}" '
                        f'to "{compile_impersonate_target(*supported_target)}"')
                return True
        return False

    def get_supported_target_strs(self) -> tuple[str]:
        return tuple(compile_impersonate_target(*target) for target in self._get_supported_targets())

    def is_target_str_supported(self, target: str):
        return self._is_target_supported(parse_impersonate_target(target))

    def _check_impersonate_target_str(self, target: str):
        assert isinstance(target, (str, NoneType))
        if target is None or not self.get_supported_target_strs():
            return
        # XXX: this will raise even if the handler doesn't support the impersonate extension
        if not self.is_target_str_supported(target):
            raise UnsupportedRequest(f'Unsupported impersonate target: {target}')

    def _resolve_from_target_str_map(self, target: str):
        return self._resolve_from_target_map(parse_impersonate_target(target))

    def _resolve_from_target_map(self, target: ImpersonateTarget):
        for supported_target, result_target in self._SUPPORTED_IMPERSONATE_TARGET_MAP.items():
            if target_within(target, supported_target):
                return result_target

    def _validate(self, request):
        super()._validate(request)
        self._check_impersonate_target_str(self.impersonate)

    def _get_impersonate_headers(self, request):
        headers = self._merge_headers(request.headers)
        if self._get_impersonate_target_str(request):
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
        lambda x: x.get_supported_target_strs(),
        [lambda _, v: isinstance(v, ImpersonateRequestHandler)]
    )
