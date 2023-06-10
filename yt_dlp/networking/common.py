from __future__ import annotations

import contextlib
import enum
import ssl
import typing
import urllib.parse
import urllib.request
import urllib.response

from .request import Request, PreparedRequest
from .utils import (
    ssl_load_certs,
    handle_request_errors
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


class RequestHandler:

    """Request Handler class

    Request handlers are class that, given an HTTP Request,
    process the request from start to finish and return an HTTP Response.

    Subclasses should re-define the _real_handle() and (optionally) _prepare_request() methods,
    which must return an instance of Response and Request respectively.

    If a Request is not to be supported by the handler, an UnsupportedRequest
    should be raised with a reason within _prepare_request().

    If an implementation makes use of an SSLContext, it should retrieve one from make_sslcontext().

    All exceptions raised by a RequestHandler should be an instance of RequestError.
    Any other exception raised will be treated as a handler issue.


    To cover some common cases, the following may be defined:

    SUPPORTED_URL_SCHEMES may contain a list of supported url schemes. Any Request
    with an url scheme not in this list will raise an UnsupportedRequest.

    SUPPORTED_PROXY_SCHEMES may contain a list of support proxy url schemes. Any Request that contains
    a proxy url with an url scheme not in this list will raise an UnsupportedRequest.

    SUPPORTED_FEATURES may contain a list of supported features, as defined in Features enum.

    RH_NAME may contain a display name for the RequestHandler.
    """

    SUPPORTED_URL_SCHEMES = None
    SUPPORTED_PROXY_SCHEMES = None
    SUPPORTED_FEATURES = []

    def __init__(self, ydl: YoutubeDL):
        self.ydl = ydl

    def make_sslcontext(self):
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
        if scheme not in (self.SUPPORTED_URL_SCHEMES or []):
            raise UnsupportedRequest(f'unsupported url scheme: "{scheme}"')
        elif scheme == 'file' and not self.ydl.params.get('enable_file_urls'):
            raise UnsupportedRequest('file:// URLs are disabled by default in yt-dlp for security reasons. '
                                     'Use --enable-file-urls to at your own risk.')

    def _check_proxies(self, prepared_request: PreparedRequest):
        if self.SUPPORTED_PROXY_SCHEMES is None:
            return
        for proxy_key, proxy_url in prepared_request.proxies.items():
            if proxy_url is None:
                continue
            if proxy_key == 'no':
                if Features.NO_PROXY not in self.SUPPORTED_FEATURES:
                    raise UnsupportedRequest('\'no\' proxy is not supported')
                continue
            if proxy_key == 'all' and Features.ALL_PROXY not in self.SUPPORTED_FEATURES:
                raise UnsupportedRequest('\'all\' proxy is not supported')

            # Unlikely this handler will use this proxy, so ignore.
            # This is to allow a case where a proxy may be set for a protocol
            # for one handler in which such protocol (and proxy) is not supported by another handler.
            if self.SUPPORTED_URL_SCHEMES is not None and proxy_key not in self.SUPPORTED_URL_SCHEMES + ['all']:
                continue

            scheme = urllib.parse.urlparse(proxy_url).scheme.lower()
            if scheme not in self.SUPPORTED_PROXY_SCHEMES:
                raise UnsupportedRequest(f'unsupported proxy type: "{scheme}"')

    @handle_request_errors
    def can_handle(self, prepared_request: PreparedRequest):
        if not isinstance(prepared_request, PreparedRequest):
            raise TypeError('Expected an instance of PreparedRequest')
        self._check_url_scheme(prepared_request)
        self._check_proxies(prepared_request)

    def _real_can_handle(self, prepared_request: PreparedRequest):
        """Redefine in subclasses"""
        return

    @handle_request_errors
    def handle(self, prepared_request: PreparedRequest) -> Response:
        if not isinstance(prepared_request, PreparedRequest):
            raise TypeError('Expected an instance of PreparedRequest')
        # XXX: do we want to make a copy of PreparedRequest here,
        # in case a handler tries to edit it?
        return self._real_handle(prepared_request)

    def _real_handle(self, prepared_request: PreparedRequest):
        """Handle a request from start to finish. Redefine in subclasses."""
        raise NotImplementedError

    def close(self):
        pass

    @utils.classproperty
    def RH_NAME(cls):
        return cls.__name__[:-2]

    @classmethod
    def rh_key(cls):
        return cls.__name__[:-2]
