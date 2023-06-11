from __future__ import annotations

import abc
import contextlib
import enum
import ssl
import typing
import urllib.parse
import urllib.request
import urllib.response

from .request import Request, PreparedRequest
from .utils import (
    wrap_request_errors
)

from .. import utils

try:
    from urllib.request import _parse_proxy
except ImportError:
    _parse_proxy = None


from .utils import make_ssl_context

from .exceptions import UnsupportedRequest

if typing.TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL
    from .response import Response


class Features(enum.Enum):
    ALL_PROXY = enum.auto()
    NO_PROXY = enum.auto()


class RequestHandlerBase(abc.ABC):
    """Base Request Handler. See RequestHandler."""
    def _validate(self, prepared_request: PreparedRequest):
        """Validate a request is supported by this handler.
         raises UnsupportedError if a request is not supported."""

    @wrap_request_errors
    def validate(self, prepared_request: PreparedRequest):
        if not isinstance(prepared_request, PreparedRequest):
            raise TypeError('Expected an instance of PreparedRequest')
        self._validate(prepared_request)

    @wrap_request_errors
    def send(self, prepared_request: PreparedRequest) -> Response:
        if not isinstance(prepared_request, PreparedRequest):
            raise TypeError('Expected an instance of PreparedRequest')
        return self._send(prepared_request)

    @abc.abstractmethod
    def _send(self, prepared_request: PreparedRequest):
        """Handle a request from start to finish. Redefine in subclasses."""

    def close(self):
        pass

    @utils.classproperty
    def RH_NAME(cls):
        return cls.__name__[:-2]

    @classmethod
    def rh_key(cls):
        return cls.__name__[:-2]


class RequestHandler(RequestHandlerBase, abc.ABC):

    """Request Handler class

    Request handlers are class that, given a Request,
    process the request from start to finish and return a Response.

    Concrete subclasses need to redefine the _send(request) method,
    which handles the underlying request logic and returns a Response.

    RH_NAME class variable may contain a display name for the RequestHandler.
    By default, this is generated from the class name.

    The concrete request handler MUST have "RH" as the suffix in the class name.

    All exceptions raised by a RequestHandler should be an instance of RequestError.
    Any other exception raised will be treated as a handler issue.

    If a Request is not supported by the handler, an UnsupportedRequest
    should be raised with a reason.
    By default, some checks are done on the request in _validate() based on the following class variables:
    - _SUPPORTED_URL_SCHEMES: may contain a list of supported url schemes.
        Any Request with an url scheme not in this list will raise an UnsupportedRequest.

    - _SUPPORTED_PROXY_SCHEMES: may contain a list of support proxy url schemes. Any Request that contains
        a proxy url with an url scheme not in this list will raise an UnsupportedRequest.

    - _SUPPORTED_FEATURES: may contain a list of supported features, as defined in Features enum.
    """

    _SUPPORTED_URL_SCHEMES: list = None
    _SUPPORTED_PROXY_SCHEMES: list = None
    _SUPPORTED_FEATURES: list = None

    def __init__(self, ydl: YoutubeDL):
        self.ydl = ydl

    def _make_sslcontext(self):
        return make_ssl_context(
            verify=not self.ydl.params.get('nocheckcertificate'),
            legacy_support=self.ydl.params.get('legacyserverconnect'),
            client_certificate=self.ydl.params.get('client_certificate'),
            client_certificate_key=self.ydl.params.get('client_certificate_key'),
            client_certificate_password=self.ydl.params.get('client_certificate_password'),
            use_certifi='no-certifi' not in self.ydl.params.get('compat_opts', [])
        )

    def _check_url_scheme(self, prepared_request: PreparedRequest):
        scheme = urllib.parse.urlparse(prepared_request.url).scheme.lower()
        if scheme not in (self._SUPPORTED_URL_SCHEMES or []):
            raise UnsupportedRequest(f'unsupported url scheme: "{scheme}"')
        elif scheme == 'file' and not self.ydl.params.get('enable_file_urls'):
            raise UnsupportedRequest('file:// URLs are disabled by default in yt-dlp for security reasons. '
                                     'Use --enable-file-urls to at your own risk.')

    def _check_proxies(self, prepared_request: PreparedRequest):
        if self._SUPPORTED_PROXY_SCHEMES is None:
            return
        for proxy_key, proxy_url in prepared_request.proxies.items():
            if proxy_url is None:
                continue
            if proxy_key == 'no':
                if Features.NO_PROXY not in (self._SUPPORTED_FEATURES or []):
                    raise UnsupportedRequest('\'no\' proxy is not supported')
                continue
            if proxy_key == 'all' and Features.ALL_PROXY not in (self._SUPPORTED_FEATURES or []):
                raise UnsupportedRequest('\'all\' proxy is not supported')

            # Unlikely this handler will use this proxy, so ignore.
            # This is to allow a case where a proxy may be set for a protocol
            # for one handler in which such protocol (and proxy) is not supported by another handler.
            if self._SUPPORTED_URL_SCHEMES is not None and proxy_key not in self._SUPPORTED_URL_SCHEMES + ['all']:
                continue

            scheme = urllib.parse.urlparse(proxy_url).scheme.lower()
            if scheme not in self._SUPPORTED_PROXY_SCHEMES:
                raise UnsupportedRequest(f'unsupported proxy type: "{scheme}"')

    def _validate(self, prepared_request):
        self._check_url_scheme(prepared_request)
        self._check_proxies(prepared_request)
