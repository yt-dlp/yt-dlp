from __future__ import annotations
import urllib.parse

from ._urllib import UrllibRH
from .common import (
    BackendRH,
    HEADRequest,
    PUTRequest,
    Request,
    RequestHandlerBroker,
)
from ..utils import RequestError


class UnsupportedRH(BackendRH):
    """
    Fallback backend adapter if a request is not supported.

    Add useful messages here of why the request may not be supported, if possible.
    E.g. a dependency is required.

    """
    def prepare_request(self, request: Request):
        scheme = urllib.parse.urlparse(request.url).scheme.lower()
        if scheme == 'file':
            raise RequestError('file:// scheme is explicitly disabled in yt-dlp for security reasons')

        for rh in self.ydl.http.get_handlers():
            if rh.SUPPORTED_SCHEMES is not None and scheme in rh.SUPPORTED_SCHEMES:
                break
        else:
            raise RequestError(f'"{scheme}:" scheme is not supported')
        raise RequestError('This request is not supported')


REQUEST_HANDLERS = [UnsupportedRH, UrllibRH]

__all__ = ['UrllibRH', 'UnsupportedRH', 'REQUEST_HANDLERS', 'Request', 'HEADRequest', 'PUTRequest', 'RequestHandlerBroker']
