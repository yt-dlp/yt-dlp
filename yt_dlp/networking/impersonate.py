from abc import ABC

from .exceptions import UnsupportedRequest
from ..utils.networking import std_headers
from .common import RequestHandler, register_preference
from ..compat.types import NoneType


class ImpersonateRequestHandler(RequestHandler, ABC):
    """
    Base class for request handlers that support browser impersonation.

    This provides a method for checking the validity of the impersonate extension,
    which can be used in _check_extensions.

    The following may be defined:
     `_SUPPORTED_IMPERSONATE_TARGETS`: a tuple of supported targets to impersonate,
        in curl-impersonate target name format. Any Request with an impersonate
        target not in this list will raise an UnsupportedRequest.
        Set to None to disable this check.

    Parameters:
    @param impersonate: the default impersonate target to use for requests.
                        Set to None to disable impersonation.
    """
    _SUPPORTED_IMPERSONATE_TARGETS: tuple = ()

    def __init__(self, *, impersonate=None, **kwargs):
        super().__init__(**kwargs)
        self.impersonate = impersonate

    def _get_impersonate_target(self, request):
        return request.extensions.get('impersonate') or self.impersonate

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        self._check_impersonate_target(extensions.get('impersonate'))

    def _check_impersonate_target(self, target):
        assert isinstance(target, (str, NoneType))
        if self._SUPPORTED_IMPERSONATE_TARGETS is None or target is None:
            return
        # XXX: this will raise even if the handler doesn't support the impersonate extension
        if target not in self._SUPPORTED_IMPERSONATE_TARGETS:
            raise UnsupportedRequest(f'Unsupported impersonate target: {target}')

    def _validate(self, request):
        super()._validate(request)
        self._check_impersonate_target(self.impersonate)

    def _get_impersonate_headers(self, request):
        headers = self._merge_headers(request.headers)
        impersonate_target = self._get_impersonate_target(request)
        if impersonate_target:
            # remove all headers present in std_headers
            headers.pop('User-Agent', None)
            for header in std_headers:
                if header in headers and std_headers[header] == headers[header]:
                    headers.pop(header, None)
        return headers


@register_preference(ImpersonateRequestHandler)
def impersonate_preference(rh, request):
    if request.extensions.get('impersonate'):
        return 1000
    return 0
