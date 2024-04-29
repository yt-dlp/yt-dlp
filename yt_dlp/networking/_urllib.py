from __future__ import annotations

import functools
import http.client
import io
import ssl
import urllib.error
import urllib.parse
import urllib.request
import urllib.response
import zlib
from urllib.request import (
    DataHandler,
    FileHandler,
    FTPHandler,
    HTTPCookieProcessor,
    HTTPDefaultErrorHandler,
    HTTPErrorProcessor,
    UnknownHandler,
)

from ._helper import (
    InstanceStoreMixin,
    add_accept_encoding_header,
    create_connection,
    create_socks_proxy_socket,
    get_redirect_method,
    make_socks_proxy_opts,
    select_proxy,
)
from .common import Features, RequestHandler, Response, register_rh
from .exceptions import (
    CertificateVerifyError,
    HTTPError,
    IncompleteRead,
    ProxyError,
    RequestError,
    SSLError,
    TransportError,
)
from ..dependencies import brotli
from ..socks import ProxyError as SocksProxyError
from ..utils import update_url_query
from ..utils.networking import normalize_url

SUPPORTED_ENCODINGS = ['gzip', 'deflate']
CONTENT_DECODE_ERRORS = [zlib.error, OSError]

if brotli:
    SUPPORTED_ENCODINGS.append('br')
    CONTENT_DECODE_ERRORS.append(brotli.error)


def _create_http_connection(http_class, source_address, *args, **kwargs):
    hc = http_class(*args, **kwargs)

    if hasattr(hc, '_create_connection'):
        hc._create_connection = create_connection

    if source_address is not None:
        hc.source_address = (source_address, 0)

    return hc


class HTTPHandler(urllib.request.AbstractHTTPHandler):
    """Handler for HTTP requests and responses.

    This class, when installed with an OpenerDirector, automatically adds
    the standard headers to every HTTP request and handles gzipped, deflated and
    brotli responses from web servers.

    Part of this code was copied from:

    http://techknack.net/python-urllib2-handlers/

    Andrew Rowls, the author of that code, agreed to release it to the
    public domain.
    """

    def __init__(self, context=None, source_address=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source_address = source_address
        self._context = context

    @staticmethod
    def _make_conn_class(base, req):
        conn_class = base
        socks_proxy = req.headers.pop('Ytdl-socks-proxy', None)
        if socks_proxy:
            conn_class = make_socks_conn_class(conn_class, socks_proxy)
        return conn_class

    def http_open(self, req):
        conn_class = self._make_conn_class(http.client.HTTPConnection, req)
        return self.do_open(functools.partial(
            _create_http_connection, conn_class, self._source_address), req)

    def https_open(self, req):
        conn_class = self._make_conn_class(http.client.HTTPSConnection, req)
        return self.do_open(
            functools.partial(
                _create_http_connection, conn_class, self._source_address),
            req, context=self._context)

    @staticmethod
    def deflate(data):
        if not data:
            return data
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error:
            return zlib.decompress(data)

    @staticmethod
    def brotli(data):
        if not data:
            return data
        return brotli.decompress(data)

    @staticmethod
    def gz(data):
        # There may be junk added the end of the file
        # We ignore it by only ever decoding a single gzip payload
        if not data:
            return data
        return zlib.decompress(data, wbits=zlib.MAX_WBITS | 16)

    def http_request(self, req):
        # According to RFC 3986, URLs can not contain non-ASCII characters, however this is not
        # always respected by websites, some tend to give out URLs with non percent-encoded
        # non-ASCII characters (see telemb.py, ard.py [#3412])
        # urllib chokes on URLs with non-ASCII characters (see http://bugs.python.org/issue3991)
        # To work around aforementioned issue we will replace request's original URL with
        # percent-encoded one
        # Since redirects are also affected (e.g. http://www.southpark.de/alle-episoden/s18e09)
        # the code of this workaround has been moved here from YoutubeDL.urlopen()
        url = req.get_full_url()
        url_escaped = normalize_url(url)

        # Substitute URL if any change after escaping
        if url != url_escaped:
            req = update_Request(req, url=url_escaped)

        return super().do_request_(req)

    def http_response(self, req, resp):
        old_resp = resp

        # Content-Encoding header lists the encodings in order that they were applied [1].
        # To decompress, we simply do the reverse.
        # [1]: https://datatracker.ietf.org/doc/html/rfc9110#name-content-encoding
        decoded_response = None
        for encoding in (e.strip() for e in reversed(resp.headers.get('Content-encoding', '').split(','))):
            if encoding == 'gzip':
                decoded_response = self.gz(decoded_response or resp.read())
            elif encoding == 'deflate':
                decoded_response = self.deflate(decoded_response or resp.read())
            elif encoding == 'br' and brotli:
                decoded_response = self.brotli(decoded_response or resp.read())

        if decoded_response is not None:
            resp = urllib.request.addinfourl(io.BytesIO(decoded_response), old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
        # Percent-encode redirect URL of Location HTTP header to satisfy RFC 3986 (see
        # https://github.com/ytdl-org/youtube-dl/issues/6457).
        if 300 <= resp.code < 400:
            location = resp.headers.get('Location')
            if location:
                # As of RFC 2616 default charset is iso-8859-1 that is respected by Python 3
                location = location.encode('iso-8859-1').decode()
                location_escaped = normalize_url(location)
                if location != location_escaped:
                    del resp.headers['Location']
                    resp.headers['Location'] = location_escaped
        return resp

    https_request = http_request
    https_response = http_response


def make_socks_conn_class(base_class, socks_proxy):
    assert issubclass(base_class, (
        http.client.HTTPConnection, http.client.HTTPSConnection))

    proxy_args = make_socks_proxy_opts(socks_proxy)

    class SocksConnection(base_class):
        _create_connection = create_connection

        def connect(self):
            self.sock = create_connection(
                (proxy_args['addr'], proxy_args['port']),
                timeout=self.timeout,
                source_address=self.source_address,
                _create_socket_func=functools.partial(
                    create_socks_proxy_socket, (self.host, self.port), proxy_args))
            if isinstance(self, http.client.HTTPSConnection):
                self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)

    return SocksConnection


class RedirectHandler(urllib.request.HTTPRedirectHandler):
    """YoutubeDL redirect handler

    The code is based on HTTPRedirectHandler implementation from CPython [1].

    This redirect handler fixes and improves the logic to better align with RFC7261
     and what browsers tend to do [2][3]

    1. https://github.com/python/cpython/blob/master/Lib/urllib/request.py
    2. https://datatracker.ietf.org/doc/html/rfc7231
    3. https://github.com/python/cpython/issues/91306
    """

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = urllib.request.HTTPRedirectHandler.http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if code not in (301, 302, 303, 307, 308):
            raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

        new_data = req.data

        # Technically the Cookie header should be in unredirected_hdrs,
        # however in practice some may set it in normal headers anyway.
        # We will remove it here to prevent any leaks.
        remove_headers = ['Cookie']

        new_method = get_redirect_method(req.get_method(), code)
        # only remove payload if method changed (e.g. POST to GET)
        if new_method != req.get_method():
            new_data = None
            remove_headers.extend(['Content-Length', 'Content-Type'])

        new_headers = {k: v for k, v in req.headers.items() if k.title() not in remove_headers}

        return urllib.request.Request(
            newurl, headers=new_headers, origin_req_host=req.origin_req_host,
            unverifiable=True, method=new_method, data=new_data)


class ProxyHandler(urllib.request.BaseHandler):
    handler_order = 100

    def __init__(self, proxies=None):
        self.proxies = proxies
        # Set default handlers
        for type in ('http', 'https', 'ftp'):
            setattr(self, '%s_open' % type, lambda r, meth=self.proxy_open: meth(r))

    def proxy_open(self, req):
        proxy = select_proxy(req.get_full_url(), self.proxies)
        if proxy is None:
            return
        if urllib.parse.urlparse(proxy).scheme.lower() in ('socks4', 'socks4a', 'socks5', 'socks5h'):
            req.add_header('Ytdl-socks-proxy', proxy)
            # yt-dlp's http/https handlers do wrapping the socket with socks
            return None
        return urllib.request.ProxyHandler.proxy_open(
            self, req, proxy, None)


class PUTRequest(urllib.request.Request):
    def get_method(self):
        return 'PUT'


class HEADRequest(urllib.request.Request):
    def get_method(self):
        return 'HEAD'


def update_Request(req, url=None, data=None, headers=None, query=None):
    req_headers = req.headers.copy()
    req_headers.update(headers or {})
    req_data = data if data is not None else req.data
    req_url = update_url_query(url or req.get_full_url(), query)
    req_get_method = req.get_method()
    if req_get_method == 'HEAD':
        req_type = HEADRequest
    elif req_get_method == 'PUT':
        req_type = PUTRequest
    else:
        req_type = urllib.request.Request
    new_req = req_type(
        req_url, data=req_data, headers=req_headers,
        origin_req_host=req.origin_req_host, unverifiable=req.unverifiable)
    if hasattr(req, 'timeout'):
        new_req.timeout = req.timeout
    return new_req


class UrllibResponseAdapter(Response):
    """
    HTTP Response adapter class for urllib addinfourl and http.client.HTTPResponse
    """

    def __init__(self, res: http.client.HTTPResponse | urllib.response.addinfourl):
        # addinfourl: In Python 3.9+, .status was introduced and .getcode() was deprecated [1]
        # HTTPResponse: .getcode() was deprecated, .status always existed [2]
        # 1. https://docs.python.org/3/library/urllib.request.html#urllib.response.addinfourl.getcode
        # 2. https://docs.python.org/3.10/library/http.client.html#http.client.HTTPResponse.status
        super().__init__(
            fp=res, headers=res.headers, url=res.url,
            status=getattr(res, 'status', None) or res.getcode(), reason=getattr(res, 'reason', None))

    def read(self, amt=None):
        try:
            return self.fp.read(amt)
        except Exception as e:
            handle_response_read_exceptions(e)
            raise e


def handle_sslerror(e: ssl.SSLError):
    if not isinstance(e, ssl.SSLError):
        return
    if isinstance(e, ssl.SSLCertVerificationError):
        raise CertificateVerifyError(cause=e) from e
    raise SSLError(cause=e) from e


def handle_response_read_exceptions(e):
    if isinstance(e, http.client.IncompleteRead):
        raise IncompleteRead(partial=len(e.partial), cause=e, expected=e.expected) from e
    elif isinstance(e, ssl.SSLError):
        handle_sslerror(e)
    elif isinstance(e, (OSError, EOFError, http.client.HTTPException, *CONTENT_DECODE_ERRORS)):
        # OSErrors raised here should mostly be network related
        raise TransportError(cause=e) from e


@register_rh
class UrllibRH(RequestHandler, InstanceStoreMixin):
    _SUPPORTED_URL_SCHEMES = ('http', 'https', 'data', 'ftp')
    _SUPPORTED_PROXY_SCHEMES = ('http', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    RH_NAME = 'urllib'

    def __init__(self, *, enable_file_urls: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.enable_file_urls = enable_file_urls
        if self.enable_file_urls:
            self._SUPPORTED_URL_SCHEMES = (*self._SUPPORTED_URL_SCHEMES, 'file')

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('cookiejar', None)
        extensions.pop('timeout', None)

    def _create_instance(self, proxies, cookiejar):
        opener = urllib.request.OpenerDirector()
        handlers = [
            ProxyHandler(proxies),
            HTTPHandler(
                debuglevel=int(bool(self.verbose)),
                context=self._make_sslcontext(),
                source_address=self.source_address),
            HTTPCookieProcessor(cookiejar),
            DataHandler(),
            UnknownHandler(),
            HTTPDefaultErrorHandler(),
            FTPHandler(),
            HTTPErrorProcessor(),
            RedirectHandler(),
        ]

        if self.enable_file_urls:
            handlers.append(FileHandler())

        for handler in handlers:
            opener.add_handler(handler)

        # Delete the default user-agent header, which would otherwise apply in
        # cases where our custom HTTP handler doesn't come into play
        # (See https://github.com/ytdl-org/youtube-dl/issues/1309 for details)
        opener.addheaders = []
        return opener

    def _send(self, request):
        headers = self._merge_headers(request.headers)
        add_accept_encoding_header(headers, SUPPORTED_ENCODINGS)
        urllib_req = urllib.request.Request(
            url=request.url,
            data=request.data,
            headers=dict(headers),
            method=request.method
        )

        opener = self._get_instance(
            proxies=self._get_proxies(request),
            cookiejar=self._get_cookiejar(request)
        )
        try:
            res = opener.open(urllib_req, timeout=self._calculate_timeout(request))
        except urllib.error.HTTPError as e:
            if isinstance(e.fp, (http.client.HTTPResponse, urllib.response.addinfourl)):
                # Prevent file object from being closed when urllib.error.HTTPError is destroyed.
                e._closer.close_called = True
                raise HTTPError(UrllibResponseAdapter(e.fp), redirect_loop='redirect error' in str(e)) from e
            raise  # unexpected
        except urllib.error.URLError as e:
            cause = e.reason  # NOTE: cause may be a string

            # proxy errors
            if 'tunnel connection failed' in str(cause).lower() or isinstance(cause, SocksProxyError):
                raise ProxyError(cause=e) from e

            handle_response_read_exceptions(cause)
            raise TransportError(cause=e) from e
        except (http.client.InvalidURL, ValueError) as e:
            # Validation errors
            # http.client.HTTPConnection raises ValueError in some validation cases
            # such as if request method contains illegal control characters [1]
            # 1. https://github.com/python/cpython/blob/987b712b4aeeece336eed24fcc87a950a756c3e2/Lib/http/client.py#L1256
            raise RequestError(cause=e) from e
        except Exception as e:
            handle_response_read_exceptions(e)
            raise  # unexpected

        return UrllibResponseAdapter(res)
