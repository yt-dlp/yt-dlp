from __future__ import annotations

import abc
import contextlib
import enum
import ssl
import typing
import urllib.parse
import urllib.request
import urllib.response
from http.cookiejar import CookieJar

from .request import Request
from .utils import (
    wrap_request_errors
)

from .. import utils
from ..utils import CaseInsensitiveDict

try:
    from urllib.request import _parse_proxy
except ImportError:
    _parse_proxy = None


from .utils import make_ssl_context

from .exceptions import UnsupportedRequest

if typing.TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL
    from .response import Response
    from typing import Union, Tuple, Optional


class Features(enum.Enum):
    ALL_PROXY = enum.auto()
    NO_PROXY = enum.auto()


class RequestHandlerBase(abc.ABC):
    """Base Request Handler. See RequestHandler."""
    def _validate(self, request: Request):
        """Validate a request is supported by this handler.
         raises UnsupportedError if a request is not supported."""

    @wrap_request_errors
    def validate(self, request: Request):
        if not isinstance(request, Request):
            raise TypeError('Expected an instance of Request')
        self._validate(request)

    @wrap_request_errors
    def send(self, request: Request) -> Response:
        if not isinstance(request, Request):
            raise TypeError('Expected an instance of Request')
        return self._send(request)

    @abc.abstractmethod
    def _send(self, request: Request):
        """Handle a request from start to finish. Redefine in subclasses."""

    def close(self):
        pass

    @utils.classproperty
    def RH_NAME(cls):
        return cls.__name__[:-2]

    @classmethod
    def rh_key(cls):
        return cls.__name__[:-2]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


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

    Parameters:
        logger: logger instance
        headers: HTTP Headers to include when sending requests.
        cookiejar: Cookiejar to use for requests.
        timeout: Socket timeout to use when sending requests.
        proxies: Proxies to use for sending requests.
        source_address: Client-side IP address to bind to for requests.
        verbose: Print debug traffic
        prefer_system_certs: Whether to prefer system certificates over other means (e.g. certifi).
        client_cert: SSL client certificate configuration.
            Tuple of (client_certificate, client_certificate_key, client_certificate_password).
        verify: Verify SSL certificates
        legacy_ssl_support: Enable various legacy SSL options.

    Some configuration options may be available for individual Requests too. In this case,
    either the Request configuration option takes precedence or they are merged.
    """

    _SUPPORTED_URL_SCHEMES: list = None
    _SUPPORTED_PROXY_SCHEMES: list = None
    _SUPPORTED_FEATURES: list = None

    def __init__(
        self,
        logger,
        *,
        headers: CaseInsensitiveDict = None,
        cookiejar: CookieJar = None,
        timeout: Union[float, int, None] = None,
        proxies: dict = None,
        source_address: str = None,
        verbose: bool = False,
        prefer_system_certs: bool = False,
        client_cert: Tuple[str, Optional[str], Optional[str]] = None,
        verify: bool = True,
        legacy_ssl_support: bool = False,  # todo: should probably generalise to some ssl_opts
    ):

        self._logger = logger
        self._headers = headers or {}
        self._cookiejar = cookiejar or CookieJar()
        self._timeout = float(timeout or 20)  # TODO: set default somewhere
        self._proxies = proxies or {}
        self._source_address = source_address
        self._verbose = verbose
        self._prefer_system_certs = prefer_system_certs
        self._client_cert = client_cert
        self._verify = verify
        self._legacy_ssl_support = legacy_ssl_support

    def _make_sslcontext(self):
        client_cert_opts = {}
        if self._client_cert:
            client_cert_opts = {
                'client_certificate': self._client_cert[0],
                'client_certificate_key': self._client_cert[1],
                'client_certificate_password': self._client_cert[2]
            }
        return make_ssl_context(
            verify=self._verify,
            legacy_support=self._legacy_ssl_support,
            use_certifi=not self._prefer_system_certs,
            **client_cert_opts
        )

    def _merge_headers(self, request_headers):
        return CaseInsensitiveDict(self._headers or {}, request_headers)

    def _check_url_scheme(self, request: Request):
        scheme = urllib.parse.urlparse(request.url).scheme.lower()
        if scheme not in (self._SUPPORTED_URL_SCHEMES or []):
            raise UnsupportedRequest(f'Unsupported url scheme: "{scheme}"')
        return scheme  # for further processing

    def _check_proxies(self, proxies):
        if self._SUPPORTED_PROXY_SCHEMES is None:
            return
        for proxy_key, proxy_url in proxies.items():
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

            # TODO: check no proxy
            # TODO: test these cases
            # TODO: test proxy is a url
            # Scheme-less proxies are not supported
            if _parse_proxy is not None and _parse_proxy(proxy_url)[0] is None:
                raise UnsupportedRequest(f'Proxy "{proxy_url}" missing scheme')

            scheme = urllib.parse.urlparse(proxy_url).scheme.lower()
            if scheme not in self._SUPPORTED_PROXY_SCHEMES:
                raise UnsupportedRequest(f'Unsupported proxy type: "{scheme}"')

    def _check_cookiejar(self, extensions):
        if not extensions.get('cookiejar'):
            return
        if not isinstance(extensions['cookiejar'], CookieJar):
            raise UnsupportedRequest('cookiejar is not a CookieJar')

    def _check_extensions(self, extensions):
        self._check_cookiejar(extensions)

    def _validate(self, request):
        self._check_url_scheme(request)
        self._check_proxies(request.proxies or self._proxies)
        self._check_extensions(request.extensions)
