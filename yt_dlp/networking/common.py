from __future__ import annotations

import abc
import copy
import enum
import functools
import io
import typing
import urllib.parse
import urllib.request
import urllib.response
from collections.abc import Iterable, Mapping
from email.message import Message
from http import HTTPStatus

from ._helper import make_ssl_context, wrap_request_errors
from .exceptions import (
    NoSupportingHandlers,
    RequestError,
    TransportError,
    UnsupportedRequest,
)
from ..compat.types import NoneType
from ..cookies import YoutubeDLCookieJar
from ..utils import (
    bug_reports_message,
    classproperty,
    deprecation_warning,
    error_to_str,
    update_url_query,
)
from ..utils.networking import HTTPHeaderDict, normalize_url

DEFAULT_TIMEOUT = 20


def register_preference(*handlers: type[RequestHandler]):
    assert all(issubclass(handler, RequestHandler) for handler in handlers)

    def outer(preference: Preference):
        @functools.wraps(preference)
        def inner(handler, *args, **kwargs):
            if not handlers or isinstance(handler, handlers):
                return preference(handler, *args, **kwargs)
            return 0
        _RH_PREFERENCES.add(inner)
        return inner
    return outer


class RequestDirector:
    """RequestDirector class

    Helper class that, when given a request, forward it to a RequestHandler that supports it.

    Preference functions in the form of func(handler, request) -> int
    can be registered into the `preferences` set. These are used to sort handlers
    in order of preference.

    @param logger: Logger instance.
    @param verbose: Print debug request information to stdout.
    """

    def __init__(self, logger, verbose=False):
        self.handlers: dict[str, RequestHandler] = {}
        self.preferences: set[Preference] = set()
        self.logger = logger  # TODO(Grub4k): default logger
        self.verbose = verbose

    def close(self):
        for handler in self.handlers.values():
            handler.close()
        self.handlers.clear()

    def add_handler(self, handler: RequestHandler):
        """Add a handler. If a handler of the same RH_KEY exists, it will overwrite it"""
        assert isinstance(handler, RequestHandler), 'handler must be a RequestHandler'
        self.handlers[handler.RH_KEY] = handler

    def _get_handlers(self, request: Request) -> list[RequestHandler]:
        """Sorts handlers by preference, given a request"""
        preferences = {
            rh: sum(pref(rh, request) for pref in self.preferences)
            for rh in self.handlers.values()
        }
        self._print_verbose('Handler preferences for this request: {}'.format(', '.join(
            f'{rh.RH_NAME}={pref}' for rh, pref in preferences.items())))
        return sorted(self.handlers.values(), key=preferences.get, reverse=True)

    def _print_verbose(self, msg):
        if self.verbose:
            self.logger.stdout(f'director: {msg}')

    def send(self, request: Request) -> Response:
        """
        Passes a request onto a suitable RequestHandler
        """
        if not self.handlers:
            raise RequestError('No request handlers configured')

        assert isinstance(request, Request)

        unexpected_errors = []
        unsupported_errors = []
        for handler in self._get_handlers(request):
            self._print_verbose(f'Checking if "{handler.RH_NAME}" supports this request.')
            try:
                handler.validate(request)
            except UnsupportedRequest as e:
                self._print_verbose(
                    f'"{handler.RH_NAME}" cannot handle this request (reason: {error_to_str(e)})')
                unsupported_errors.append(e)
                continue

            self._print_verbose(f'Sending request via "{handler.RH_NAME}"')
            try:
                response = handler.send(request)
            except RequestError:
                raise
            except Exception as e:
                self.logger.error(
                    f'[{handler.RH_NAME}] Unexpected error: {error_to_str(e)}{bug_reports_message()}',
                    is_error=False)
                unexpected_errors.append(e)
                continue

            assert isinstance(response, Response)
            return response

        raise NoSupportingHandlers(unsupported_errors, unexpected_errors)


_REQUEST_HANDLERS = {}


def register_rh(handler):
    """Register a RequestHandler class"""
    assert issubclass(handler, RequestHandler), f'{handler} must be a subclass of RequestHandler'
    assert handler.RH_KEY not in _REQUEST_HANDLERS, f'RequestHandler {handler.RH_KEY} already registered'
    _REQUEST_HANDLERS[handler.RH_KEY] = handler
    return handler


class Features(enum.Enum):
    ALL_PROXY = enum.auto()
    NO_PROXY = enum.auto()


class RequestHandler(abc.ABC):

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
    - `_SUPPORTED_URL_SCHEMES`: a tuple of supported url schemes.
        Any Request with an url scheme not in this list will raise an UnsupportedRequest.

    - `_SUPPORTED_PROXY_SCHEMES`: a tuple of support proxy url schemes. Any Request that contains
        a proxy url with an url scheme not in this list will raise an UnsupportedRequest.

    - `_SUPPORTED_FEATURES`: a tuple of supported features, as defined in Features enum.

    The above may be set to None to disable the checks.

    Parameters:
    @param logger: logger instance
    @param headers: HTTP Headers to include when sending requests.
    @param cookiejar: Cookiejar to use for requests.
    @param timeout: Socket timeout to use when sending requests.
    @param proxies: Proxies to use for sending requests.
    @param source_address: Client-side IP address to bind to for requests.
    @param verbose: Print debug request and traffic information to stdout.
    @param prefer_system_certs: Whether to prefer system certificates over other means (e.g. certifi).
    @param client_cert: SSL client certificate configuration.
            dict with {client_certificate, client_certificate_key, client_certificate_password}
    @param verify: Verify SSL certificates
    @param legacy_ssl_support: Enable legacy SSL options such as legacy server connect and older cipher support.

    Some configuration options may be available for individual Requests too. In this case,
    either the Request configuration option takes precedence or they are merged.

    Requests may have additional optional parameters defined as extensions.
     RequestHandler subclasses may choose to support custom extensions.

    If an extension is supported, subclasses should extend _check_extensions(extensions)
    to pop and validate the extension.
    - Extensions left in `extensions` are treated as unsupported and UnsupportedRequest will be raised.

    The following extensions are defined for RequestHandler:
    - `cookiejar`: Cookiejar to use for this request.
    - `timeout`: socket timeout to use for this request.
    - `legacy_ssl`: Enable legacy SSL options for this request. See legacy_ssl_support.
    To enable these, add extensions.pop('<extension>', None) to _check_extensions

    Apart from the url protocol, proxies dict may contain the following keys:
    - `all`: proxy to use for all protocols. Used as a fallback if no proxy is set for a specific protocol.
    - `no`: comma seperated list of hostnames (optionally with port) to not use a proxy for.
    Note: a RequestHandler may not support these, as defined in `_SUPPORTED_FEATURES`.

    """

    _SUPPORTED_URL_SCHEMES = ()
    _SUPPORTED_PROXY_SCHEMES = ()
    _SUPPORTED_FEATURES = ()

    def __init__(
        self, *,
        logger,  # TODO(Grub4k): default logger
        headers: HTTPHeaderDict = None,
        cookiejar: YoutubeDLCookieJar = None,
        timeout: float | int | None = None,
        proxies: dict | None = None,
        source_address: str | None = None,
        verbose: bool = False,
        prefer_system_certs: bool = False,
        client_cert: dict[str, str | None] | None = None,
        verify: bool = True,
        legacy_ssl_support: bool = False,
        **_,
    ):

        self._logger = logger
        self.headers = headers or {}
        self.cookiejar = cookiejar if cookiejar is not None else YoutubeDLCookieJar()
        self.timeout = float(timeout or DEFAULT_TIMEOUT)
        self.proxies = proxies or {}
        self.source_address = source_address
        self.verbose = verbose
        self.prefer_system_certs = prefer_system_certs
        self._client_cert = client_cert or {}
        self.verify = verify
        self.legacy_ssl_support = legacy_ssl_support
        super().__init__()

    def _make_sslcontext(self, legacy_ssl_support=None):
        return make_ssl_context(
            verify=self.verify,
            legacy_support=legacy_ssl_support if legacy_ssl_support is not None else self.legacy_ssl_support,
            use_certifi=not self.prefer_system_certs,
            **self._client_cert,
        )

    def _merge_headers(self, request_headers):
        return HTTPHeaderDict(self.headers, request_headers)

    def _calculate_timeout(self, request):
        return float(request.extensions.get('timeout') or self.timeout)

    def _get_cookiejar(self, request):
        cookiejar = request.extensions.get('cookiejar')
        return self.cookiejar if cookiejar is None else cookiejar

    def _get_proxies(self, request):
        return (request.proxies or self.proxies).copy()

    def _check_url_scheme(self, request: Request):
        scheme = urllib.parse.urlparse(request.url).scheme.lower()
        if self._SUPPORTED_URL_SCHEMES is not None and scheme not in self._SUPPORTED_URL_SCHEMES:
            raise UnsupportedRequest(f'Unsupported url scheme: "{scheme}"')
        return scheme  # for further processing

    def _check_proxies(self, proxies):
        for proxy_key, proxy_url in proxies.items():
            if proxy_url is None:
                continue
            if proxy_key == 'no':
                if self._SUPPORTED_FEATURES is not None and Features.NO_PROXY not in self._SUPPORTED_FEATURES:
                    raise UnsupportedRequest('"no" proxy is not supported')
                continue
            if (
                proxy_key == 'all'
                and self._SUPPORTED_FEATURES is not None
                and Features.ALL_PROXY not in self._SUPPORTED_FEATURES
            ):
                raise UnsupportedRequest('"all" proxy is not supported')

            # Unlikely this handler will use this proxy, so ignore.
            # This is to allow a case where a proxy may be set for a protocol
            # for one handler in which such protocol (and proxy) is not supported by another handler.
            if self._SUPPORTED_URL_SCHEMES is not None and proxy_key not in (*self._SUPPORTED_URL_SCHEMES, 'all'):
                continue

            if self._SUPPORTED_PROXY_SCHEMES is None:
                # Skip proxy scheme checks
                continue

            try:
                if urllib.request._parse_proxy(proxy_url)[0] is None:
                    # Scheme-less proxies are not supported
                    raise UnsupportedRequest(f'Proxy "{proxy_url}" missing scheme')
            except ValueError as e:
                # parse_proxy may raise on some invalid proxy urls such as "/a/b/c"
                raise UnsupportedRequest(f'Invalid proxy url "{proxy_url}": {e}')

            scheme = urllib.parse.urlparse(proxy_url).scheme.lower()
            if scheme not in self._SUPPORTED_PROXY_SCHEMES:
                raise UnsupportedRequest(f'Unsupported proxy type: "{scheme}"')

    def _check_extensions(self, extensions):
        """Check extensions for unsupported extensions. Subclasses should extend this."""
        assert isinstance(extensions.get('cookiejar'), (YoutubeDLCookieJar, NoneType))
        assert isinstance(extensions.get('timeout'), (float, int, NoneType))
        assert isinstance(extensions.get('legacy_ssl'), (bool, NoneType))

    def _validate(self, request):
        self._check_url_scheme(request)
        self._check_proxies(request.proxies or self.proxies)
        extensions = request.extensions.copy()
        self._check_extensions(extensions)
        if extensions:
            # TODO: add support for optional extensions
            raise UnsupportedRequest(f'Unsupported extensions: {", ".join(extensions.keys())}')

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
        pass

    def close(self):  # noqa: B027
        pass

    @classproperty
    def RH_NAME(cls):
        return cls.__name__[:-2]

    @classproperty
    def RH_KEY(cls):
        assert cls.__name__.endswith('RH'), 'RequestHandler class names must end with "RH"'
        return cls.__name__[:-2]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Request:
    """
    Represents a request to be made.
    Partially backwards-compatible with urllib.request.Request.

    @param url: url to send. Will be sanitized.
    @param data: payload data to send. Must be bytes, iterable of bytes, a file-like object or None
    @param headers: headers to send.
    @param proxies: proxy dict mapping of proto:proxy to use for the request and any redirects.
    @param query: URL query parameters to update the url with.
    @param method: HTTP method to use. If no method specified, will use POST if payload data is present else GET
    @param extensions: Dictionary of Request extensions to add, as supported by handlers.
    """

    def __init__(
            self,
            url: str,
            data: RequestData = None,
            headers: typing.Mapping | None = None,
            proxies: dict | None = None,
            query: dict | None = None,
            method: str | None = None,
            extensions: dict | None = None,
    ):

        self._headers = HTTPHeaderDict()
        self._data = None

        if query:
            url = update_url_query(url, query)

        self.url = url
        self.method = method
        if headers:
            self.headers = headers
        self.data = data  # note: must be done after setting headers
        self.proxies = proxies or {}
        self.extensions = extensions or {}

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        if not isinstance(url, str):
            raise TypeError('url must be a string')
        elif url.startswith('//'):
            url = 'http:' + url
        self._url = normalize_url(url)

    @property
    def method(self):
        return self._method or ('POST' if self.data is not None else 'GET')

    @method.setter
    def method(self, method):
        if method is None:
            self._method = None
        elif isinstance(method, str):
            self._method = method.upper()
        else:
            raise TypeError('method must be a string')

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: RequestData):
        # Try catch some common mistakes
        if data is not None and (
            not isinstance(data, (bytes, io.IOBase, Iterable)) or isinstance(data, (str, Mapping))
        ):
            raise TypeError('data must be bytes, iterable of bytes, or a file-like object')

        if data == self._data and self._data is None:
            self.headers.pop('Content-Length', None)

        # https://docs.python.org/3/library/urllib.request.html#urllib.request.Request.data
        if data != self._data:
            if self._data is not None:
                self.headers.pop('Content-Length', None)
            self._data = data

        if self._data is None:
            self.headers.pop('Content-Type', None)

        if 'Content-Type' not in self.headers and self._data is not None:
            self.headers['Content-Type'] = 'application/x-www-form-urlencoded'

    @property
    def headers(self) -> HTTPHeaderDict:
        return self._headers

    @headers.setter
    def headers(self, new_headers: Mapping):
        """Replaces headers of the request. If not a HTTPHeaderDict, it will be converted to one."""
        if isinstance(new_headers, HTTPHeaderDict):
            self._headers = new_headers
        elif isinstance(new_headers, Mapping):
            self._headers = HTTPHeaderDict(new_headers)
        else:
            raise TypeError('headers must be a mapping')

    def update(self, url=None, data=None, headers=None, query=None, extensions=None):
        self.data = data if data is not None else self.data
        self.headers.update(headers or {})
        self.extensions.update(extensions or {})
        self.url = update_url_query(url or self.url, query or {})

    def copy(self):
        return self.__class__(
            url=self.url,
            headers=copy.deepcopy(self.headers),
            proxies=copy.deepcopy(self.proxies),
            data=self._data,
            extensions=copy.copy(self.extensions),
            method=self._method,
        )


HEADRequest = functools.partial(Request, method='HEAD')
PUTRequest = functools.partial(Request, method='PUT')


class Response(io.IOBase):
    """
    Base class for HTTP response adapters.

    By default, it provides a basic wrapper for a file-like response object.

    Interface partially backwards-compatible with addinfourl and http.client.HTTPResponse.

    @param fp: Original, file-like, response.
    @param url: URL that this is a response of.
    @param headers: response headers.
    @param status: Response HTTP status code. Default is 200 OK.
    @param reason: HTTP status reason. Will use built-in reasons based on status code if not provided.
    @param extensions: Dictionary of handler-specific response extensions.
    """

    def __init__(
            self,
            fp: io.IOBase,
            url: str,
            headers: Mapping[str, str],
            status: int = 200,
            reason: str | None = None,
            extensions: dict | None = None,
    ):

        self.fp = fp
        self.headers = Message()
        for name, value in headers.items():
            self.headers.add_header(name, value)
        self.status = status
        self.url = url
        try:
            self.reason = reason or HTTPStatus(status).phrase
        except ValueError:
            self.reason = None
        self.extensions = extensions or {}

    def readable(self):
        return self.fp.readable()

    def read(self, amt: int | None = None) -> bytes:
        # Expected errors raised here should be of type RequestError or subclasses.
        # Subclasses should redefine this method with more precise error handling.
        try:
            return self.fp.read(amt)
        except Exception as e:
            raise TransportError(cause=e) from e

    def close(self):
        self.fp.close()
        return super().close()

    def get_header(self, name, default=None):
        """Get header for name.
        If there are multiple matching headers, return all seperated by comma."""
        headers = self.headers.get_all(name)
        if not headers:
            return default
        if name.title() == 'Set-Cookie':
            # Special case, only get the first one
            # https://www.rfc-editor.org/rfc/rfc9110.html#section-5.3-4.1
            return headers[0]
        return ', '.join(headers)

    # The following methods are for compatability reasons and are deprecated
    @property
    def code(self):
        deprecation_warning('Response.code is deprecated, use Response.status', stacklevel=2)
        return self.status

    def getcode(self):
        deprecation_warning('Response.getcode() is deprecated, use Response.status', stacklevel=2)
        return self.status

    def geturl(self):
        deprecation_warning('Response.geturl() is deprecated, use Response.url', stacklevel=2)
        return self.url

    def info(self):
        deprecation_warning('Response.info() is deprecated, use Response.headers', stacklevel=2)
        return self.headers

    def getheader(self, name, default=None):
        deprecation_warning('Response.getheader() is deprecated, use Response.get_header', stacklevel=2)
        return self.get_header(name, default)


if typing.TYPE_CHECKING:
    RequestData = bytes | Iterable[bytes] | typing.IO | None
    Preference = typing.Callable[[RequestHandler, Request], int]

_RH_PREFERENCES: set[Preference] = set()
