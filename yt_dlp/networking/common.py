from __future__ import annotations

import contextlib
import enum
import ssl
import typing
import urllib.parse
import urllib.request
import urllib.response

from .request import Request
from .utils import (
    ssl_load_certs,
    handle_request_errors
)

from .. import utils

try:
    from urllib.request import _parse_proxy
except ImportError:
    _parse_proxy = None

from ..utils import (
    CaseInsensitiveDict,
    YoutubeDLError,
    remove_start,
)

from .utils import make_ssl_context

from .exceptions import UnsupportedRequest

if typing.TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL


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

    SUPPORTED_ENCODINGS may contain a list of supported content encodings for the Accept-Encoding header.

    SUPPORTED_FEATURES may contain a list of supported features, as defined in Features enum.

    RH_NAME may contain a display name for the RequestHandler.
    """

    SUPPORTED_URL_SCHEMES = None
    SUPPORTED_PROXY_SCHEMES = None
    SUPPORTED_ENCODINGS = None
    SUPPORTED_FEATURES = []

    def __init__(self, ydl: YoutubeDL):
        self.ydl = ydl
        self.cookiejar = self.ydl.cookiejar

    def make_sslcontext(self):
        return make_ssl_context(
            verify=not self.ydl.params.get('nocheckcertificate'),
            legacy_support=self.ydl.params.get('legacyserverconnect'),
            client_certificate=self.ydl.params.get('client_certificate'),
            client_certificate_key=self.ydl.params.get('client_certificate_key'),
            client_certificate_password=self.ydl.params.get('client_certificate_password'),
            use_certifi='no-certifi' not in self.ydl.params.get('compat_opts', [])
        )

    def _check_url_scheme(self, request: Request):
        scheme = urllib.parse.urlparse(request.url).scheme.lower()
        if scheme not in (self.SUPPORTED_URL_SCHEMES or []):
            raise UnsupportedRequest(f'unsupported url scheme: "{scheme}"')
        elif scheme == 'file' and not self.ydl.params.get('enable_file_urls'):
            raise UnsupportedRequest('file:// URLs are disabled by default in yt-dlp for security reasons. '
                                     'Use --enable-file-urls to at your own risk.')

    def _check_proxies(self, request: Request):
        if self.SUPPORTED_PROXY_SCHEMES is None:
            return
        for proxy_key, proxy_url in request.proxies.items():
            if proxy_url is None:
                continue
            if proxy_key == 'no':
                if Features.NO_PROXY not in self.SUPPORTED_FEATURES:
                    raise UnsupportedRequest('\'no\' proxy is not supported')
                continue
            if proxy_key == 'all' and Features.ALL_PROXY not in self.SUPPORTED_FEATURES:
                # XXX: If necessary, we could break up all_proxy here using SUPPORTED_SCHEMES
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
    def can_handle(self, request, fatal=False):
        try:
            self.prepare_request(request)
        except UnsupportedRequest:
            if fatal:
                raise
            return False
        return True

    def _prepare_proxies(self, request):
        request.proxies = request.proxies or self.ydl.proxies
        req_proxy = request.headers.pop('Ytdl-request-proxy', None)
        if req_proxy:
            request.proxies = {'all': req_proxy}

        for proxy_key, proxy_url in request.proxies.items():
            if proxy_url == '__noproxy__':  # compat
                request.proxies[proxy_key] = None
                continue
            if proxy_key == 'no':  # special case
                continue
            if proxy_url is not None and _parse_proxy is not None:
                # Ensure proxies without a scheme are http.
                proxy_scheme = _parse_proxy(proxy_url)[0]
                if proxy_scheme is None:
                    request.proxies[proxy_key] = 'http://' + remove_start(proxy_url, '//')

    def _prepare_headers(self, request):
        request.headers = CaseInsensitiveDict(self.ydl.params.get('http_headers', {}), request.headers)
        if 'Youtubedl-no-compression' in request.headers:  # compat
            del request.headers['Youtubedl-no-compression']
            request.headers['Accept-Encoding'] = 'identity'

        if self.SUPPORTED_ENCODINGS and 'Accept-Encoding' not in request.headers:
            request.headers['Accept-Encoding'] = ', '.join(self.SUPPORTED_ENCODINGS)

        if 'Accept-Encoding' not in request.headers:
            request.headers['Accept-Encoding'] = 'identity'

    @handle_request_errors
    def prepare_request(self, request: Request):
        """Returns a new Request prepared for this handler."""
        if not isinstance(request, Request):
            raise TypeError('Expected an instance of Request')
        request = request.copy()
        self._check_url_scheme(request)
        self._prepare_headers(request)
        self._prepare_proxies(request)
        request.timeout = float(
            request.timeout or self.ydl.params.get('socket_timeout') or 20)  # do not accept 0
        self._check_proxies(request)
        return self._prepare_request(request)

    def _prepare_request(self, request: Request):
        """Returns a new Request prepared for this handler. Redefine in subclasses for custom handling"""
        return request

    @handle_request_errors
    def handle(self, request: Request):
        request = self.prepare_request(request)
        assert isinstance(request, Request)
        return self._real_handle(request)

    def _real_handle(self, request: Request):
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
