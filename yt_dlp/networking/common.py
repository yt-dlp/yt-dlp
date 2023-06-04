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

    SUPPORTED_SCHEMES may contain a list of supported url schemes. Any Request
    with an url scheme not in this list will raise an UnsupportedRequest.

    SUPPORTED_PROXY_SCHEMES may contain a list of support proxy url schemes. Any Request that contains
    a proxy url with an url scheme not in this list will raise an UnsupportedRequest.

    SUPPORTED_ENCODINGS may contain a list of supported content encodings for the Accept-Encoding header.

    SUPPORTED_FEATURES may contain a list of supported features, as defined in Features enum.

    RH_NAME may contain a display name for the RequestHandler.
    """

    SUPPORTED_SCHEMES = None
    SUPPORTED_PROXY_SCHEMES = None
    SUPPORTED_ENCODINGS = None
    SUPPORTED_FEATURES = []

    def __init__(self, ydl: YoutubeDL):
        self.ydl = ydl
        self.cookiejar = self.ydl.cookiejar

    def make_sslcontext(self):
        """
        Make a new SSLContext configured for this request handler.
        This assumes HTTP 1.1 is used.
        """
        verify = not self.ydl.params.get('nocheckcertificate')
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = verify
        context.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE

        # Some servers may reject requests if ALPN extension is not sent. See:
        # https://github.com/python/cpython/issues/85140
        # https://github.com/yt-dlp/yt-dlp/issues/3878
        with contextlib.suppress(NotImplementedError):
            context.set_alpn_protocols(['http/1.1'])
        if verify:
            ssl_load_certs(context, self.ydl.params)

        if self.ydl.params.get('legacyserverconnect'):
            context.options |= 4  # SSL_OP_LEGACY_SERVER_CONNECT
            context.set_ciphers('DEFAULT')  # compat

        elif ssl.OPENSSL_VERSION_INFO >= (1, 1, 1) and not ssl.OPENSSL_VERSION.startswith('LibreSSL'):
            # Use the default SSL ciphers and minimum TLS version settings from Python 3.10 [1].
            # This is to ensure consistent behavior across Python versions and libraries, and help avoid fingerprinting
            # in some situations [2][3].
            # Python 3.10 only supports OpenSSL 1.1.1+ [4]. Because this change is likely
            # untested on older versions, we only apply this to OpenSSL 1.1.1+ to be safe.
            # LibreSSL is excluded until further investigation due to cipher support issues [5][6].
            # 1. https://github.com/python/cpython/commit/e983252b516edb15d4338b0a47631b59ef1e2536
            # 2. https://github.com/yt-dlp/yt-dlp/issues/4627
            # 3. https://github.com/yt-dlp/yt-dlp/pull/5294
            # 4. https://peps.python.org/pep-0644/
            # 5. https://peps.python.org/pep-0644/#libressl-support
            # 6. https://github.com/yt-dlp/yt-dlp/commit/5b9f253fa0aee996cf1ed30185d4b502e00609c4#commitcomment-89054368
            context.set_ciphers(
                '@SECLEVEL=2:ECDH+AESGCM:ECDH+CHACHA20:ECDH+AES:DHE+AES:!aNULL:!eNULL:!aDSS:!SHA1:!AESCCM')
            context.minimum_version = ssl.TLSVersion.TLSv1_2

        client_certfile = self.ydl.params.get('client_certificate')
        if client_certfile:
            try:
                context.load_cert_chain(
                    client_certfile, keyfile=self.ydl.params.get('client_certificate_key'),
                    password=self.ydl.params.get('client_certificate_password'))
            except ssl.SSLError:
                raise YoutubeDLError('Unable to load client certificate')

            if getattr(context, 'post_handshake_auth', None) is not None:
                context.post_handshake_auth = True

        return context

    def _check_scheme(self, request: Request):
        scheme = urllib.parse.urlparse(request.url).scheme.lower()
        if self.SUPPORTED_SCHEMES is not None and scheme not in self.SUPPORTED_SCHEMES:
            raise UnsupportedRequest(f'unsupported scheme: "{scheme}"')

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
            if self.SUPPORTED_SCHEMES is not None and proxy_key not in self.SUPPORTED_SCHEMES + ['all']:
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
        self._check_scheme(request)
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
