from __future__ import annotations

import contextlib
import errno
import functools
import gzip
import http.client
import io
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
import urllib.response
import zlib
from typing import Union
from urllib.request import (
    FTPHandler,
    HTTPDefaultErrorHandler,
    HTTPErrorProcessor,
    UnknownHandler,
    HTTPCookieProcessor,
    DataHandler,
)

from .common import Response, RequestHandler
from .utils import (
    get_redirect_method,
    select_proxy,
    make_socks_proxy_opts,
    ssl_load_certs,
)
from ..dependencies import brotli
from ..socks import sockssocket
from ..utils import (
    escape_url,
    extract_basic_auth,
    sanitize_url,
    update_url_query,
)
from .exceptions import (
    TransportError,
    HTTPError,
    IncompleteRead,
    SSLError,
    ProxyError
)

CONTENT_DECODE_ERRORS = [zlib.error, OSError]

SUPPORTED_ENCODINGS = [
    'gzip', 'deflate'
]

if brotli:
    SUPPORTED_ENCODINGS.append('br')
    CONTENT_DECODE_ERRORS.append(brotli.error)


def _create_http_connection(ydl_handler, http_class, is_https, *args, **kwargs):
    hc = http_class(*args, **kwargs)
    source_address = ydl_handler._params.get('source_address')

    if source_address is not None:
        # This is to workaround _create_connection() from socket where it will try all
        # address data from getaddrinfo() including IPv6. This filters the result from
        # getaddrinfo() based on the source_address value.
        # This is based on the cpython socket.create_connection() function.
        # https://github.com/python/cpython/blob/master/Lib/socket.py#L691
        def _create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
            host, port = address
            err = None
            addrs = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
            af = socket.AF_INET if '.' in source_address[0] else socket.AF_INET6
            ip_addrs = [addr for addr in addrs if addr[0] == af]
            if addrs and not ip_addrs:
                ip_version = 'v4' if af == socket.AF_INET else 'v6'
                raise OSError(
                    "No remote IP%s addresses available for connect, can't use '%s' as source address"
                    % (ip_version, source_address[0]))
            for res in ip_addrs:
                af, socktype, proto, canonname, sa = res
                sock = None
                try:
                    sock = socket.socket(af, socktype, proto)
                    if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                        sock.settimeout(timeout)
                    sock.bind(source_address)
                    sock.connect(sa)
                    err = None  # Explicitly break reference cycle
                    return sock
                except OSError as _:
                    err = _
                    if sock is not None:
                        sock.close()
            if err is not None:
                raise err
            else:
                raise OSError('getaddrinfo returns an empty list')
        if hasattr(hc, '_create_connection'):
            hc._create_connection = _create_connection
        hc.source_address = (source_address, 0)

    return hc


class YoutubeDLHandler(urllib.request.AbstractHTTPHandler):
    """Handler for HTTP requests and responses.

    This class, when installed with an OpenerDirector, automatically adds
    the standard headers to every HTTP request and handles gzipped and
    deflated responses from web servers. If compression is to be avoided in
    a particular request, the original request in the program code only has
    to include the HTTP header "Youtubedl-no-compression", which will be
    removed before making the real request.

    Part of this code was copied from:

    http://techknack.net/python-urllib2-handlers/

    Andrew Rowls, the author of that code, agreed to release it to the
    public domain.
    """

    def __init__(self, params, context=None, check_hostname=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._params = params
        self._context = context
        self._check_hostname = check_hostname

    @staticmethod
    def _make_conn_class(base, req):
        conn_class = base
        socks_proxy = req.headers.pop('Ytdl-socks-proxy', None)
        if socks_proxy:
            conn_class = make_socks_conn_class(conn_class, socks_proxy)
        return conn_class

    def http_open(self, req):
        conn_class = self._make_conn_class(http.client.HTTPConnection, req)
        return self.do_open(functools.partial(_create_http_connection, self, conn_class, False), req)

    def https_open(self, req):
        conn_class = self._make_conn_class(http.client.HTTPSConnection, req)
        return self.do_open(
            functools.partial(_create_http_connection, self, conn_class, True),
            req, check_hostname=self._check_hostname, context=self._context)

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
        url_escaped = escape_url(url)

        # Substitute URL if any change after escaping
        if url != url_escaped:
            req = update_Request(req, url=url_escaped)

        return super().do_request_(req)

    def http_response(self, req, resp):
        old_resp = resp
        # gzip
        if resp.headers.get('Content-encoding', '') == 'gzip':
            content = resp.read()
            gz = gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb')
            try:
                uncompressed = io.BytesIO(gz.read())
            except OSError as original_ioerror:
                # There may be junk add the end of the file
                # See http://stackoverflow.com/q/4928560/35070 for details
                for i in range(1, 1024):
                    try:
                        gz = gzip.GzipFile(fileobj=io.BytesIO(content[:-i]), mode='rb')
                        uncompressed = io.BytesIO(gz.read())
                    except OSError:
                        continue
                    break
                else:
                    raise original_ioerror
            resp = urllib.response.addinfourl(uncompressed, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
            del resp.headers['Content-encoding']
        # deflate
        if resp.headers.get('Content-encoding', '') == 'deflate':
            gz = io.BytesIO(self.deflate(resp.read()))
            resp = urllib.response.addinfourl(gz, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
            del resp.headers['Content-encoding']
        # brotli
        if resp.headers.get('Content-encoding', '') == 'br':
            resp = urllib.response.addinfourl(
                io.BytesIO(self.brotli(resp.read())), old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
            del resp.headers['Content-encoding']
        # Percent-encode redirect URL of Location HTTP header to satisfy RFC 3986 (see
        # https://github.com/ytdl-org/youtube-dl/issues/6457).
        if 300 <= resp.code < 400:
            location = resp.headers.get('Location')
            if location:
                # As of RFC 2616 default charset is iso-8859-1 that is respected by python 3
                location = location.encode('iso-8859-1').decode()
                location_escaped = escape_url(location)
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
        def connect(self):
            self.sock = sockssocket()
            self.sock.setproxy(**proxy_args)
            if type(self.timeout) in (int, float):
                self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))

            if isinstance(self, http.client.HTTPSConnection):
                if hasattr(self, '_context'):  # Python > 2.6
                    self.sock = self._context.wrap_socket(
                        self.sock, server_hostname=self.host)
                else:
                    self.sock = ssl.wrap_socket(self.sock)

    return SocksConnection


class YDLRedirectHandler(urllib.request.HTTPRedirectHandler):
    """YoutubeDL redirect handler

    The code is based on HTTPRedirectHandler implementation from CPython [1].

    This redirect handler has the following improvements:
     - introduces support for HTTP response status code
       308 Permanent Redirect [2] used by some sites [3]
     - improved redirect method handling
     - only strip payload/headers when method changes from POST to GET


    1. https://github.com/python/cpython/blob/master/Lib/urllib/request.py
    2. https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/308
    3. https://github.com/ytdl-org/youtube-dl/issues/28768
    """

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = urllib.request.HTTPRedirectHandler.http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Return a Request or None in response to a redirect.

        This is called by the http_error_30x methods when a
        redirection response is received.  If a redirection should
        take place, return a new Request to allow http_error_30x to
        perform the redirect.  Otherwise, raise HTTPError if no-one
        else should try to handle this url.  Return None if you can't
        but another Handler might.
        """
        m = req.get_method()
        if code not in (301, 302, 303, 307, 308):
            raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)

        # Strictly (according to RFC 2616), 301 or 302 in response to
        # a POST MUST NOT cause a redirection without confirmation
        # from the user (of urllib.request, in this case).  In practice,
        # essentially all clients do redirect in this case, so we do
        # the same.

        # Be conciliant with URIs containing a space.  This is mainly
        # redundant with the more complete encoding done in http_error_302(),
        # but it is kept for compatibility with other callers.
        newurl = newurl.replace(' ', '%20')

        new_data = req.data
        remove_headers = []
        new_method = get_redirect_method(m, code)

        # only remove payload if method changed (e.g. POST to GET)
        if new_method != m:
            new_data = None
            remove_headers.extend(['Content-Length', 'Content-Type'])

        new_headers = {k: v for k, v in req.headers.items() if k.lower() not in remove_headers}

        return urllib.request.Request(
            newurl, headers=new_headers, origin_req_host=req.origin_req_host,
            unverifiable=True, method=new_method, data=new_data)


class YDLNoRedirectHandler(urllib.request.BaseHandler):

    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


class PUTRequest(urllib.request.Request):
    def get_method(self):
        return 'PUT'


class HEADRequest(urllib.request.Request):
    def get_method(self):
        return 'HEAD'


def update_Request(req, url=None, data=None, headers=None, query=None):
    req_headers = req.headers.copy()
    req_headers.update(headers or {})
    req_data = data or req.data
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


class YDLProxyHandler(urllib.request.BaseHandler):
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
        if urllib.parse.urlparse(proxy).scheme.lower() in ('socks', 'socks4', 'socks4a', 'socks5'):
            req.add_header('Ytdl-socks-proxy', proxy)
            # yt-dlp's http/https handlers do wrapping the socket with socks
            return None
        return urllib.request.ProxyHandler.proxy_open(
            self, req, proxy, None)


class UrllibHTTPResponseAdapter(Response):
    """
    HTTP Response adapter class for urllib addinfourl and http.client.HTTPResponse
    """

    def __init__(self, res: Union[http.client.HTTPResponse, urllib.response.addinfourl]):
        # addinfourl: In Python 3.9+, .status was introduced and .getcode() was deprecated [1]
        # HTTPResponse: .getcode() was deprecated, .status always existed [2]
        # 1. https://docs.python.org/3/library/urllib.request.html#urllib.response.addinfourl.getstatus
        # 2. https://docs.python.org/3.10/library/http.client.html#http.client.HTTPResponse.status
        super().__init__(
            raw=res, headers=res.headers, url=res.url,
            status=getattr(res, 'status', None) or res.getcode(), reason=getattr(res, 'reason', None))

    def read(self, amt=None):
        try:
            return self.raw.read(amt)
        except Exception as e:
            handle_response_read_exceptions(e)
            raise e


def handle_sslerror(e):
    if not isinstance(e, ssl.SSLError):
        return
    if e.errno == errno.ETIMEDOUT:
        raise TransportError(cause=e) from e
    raise SSLError(msg=str(e.reason or e), cause=e) from e


def sanitized_Request(url, *args, **kwargs):
    url, auth_header = extract_basic_auth(escape_url(sanitize_url(url)))
    if auth_header is not None:
        headers = args[1] if len(args) >= 2 else kwargs.setdefault('headers', {})
        headers['Authorization'] = auth_header
    return urllib.request.Request(url, *args, **kwargs)


def handle_response_read_exceptions(e):
    try:
        raise e
    except http.client.IncompleteRead as e:
        raise IncompleteRead(partial=e.partial, cause=e, expected=e.expected)

    except ssl.SSLError as e:
        handle_sslerror(e)

    except (OSError, http.client.HTTPException, *CONTENT_DECODE_ERRORS) as e:
        # OSErrors raised here should mostly be network related
        if 'tunnel connection failed' in str(e).lower():
            raise ProxyError(cause=e)
        raise TransportError(cause=e)


class UrllibRH(RequestHandler):
    SUPPORTED_SCHEMES = ['http', 'https', 'data', 'ftp']
    _SUPPORTED_ENCODINGS = SUPPORTED_ENCODINGS
    NAME = 'urllib'

    def __init__(self, ydl):
        super().__init__(ydl)
        self._openers = {}

    def _create_opener(self, proxies=None, allow_redirects=True):
        opener = urllib.request.OpenerDirector()
        handlers = [
            YDLProxyHandler(proxies),
            HTTPCookieProcessor(self.cookiejar),
            YoutubeDLHandler(
                self.ydl.params, debuglevel=int(bool(self.ydl.params.get('debug_printtraffic'))),
                context=self.make_sslcontext()),
            DataHandler(),
            UnknownHandler(),
            HTTPDefaultErrorHandler(),
            FTPHandler(),
            HTTPErrorProcessor(),
            YDLRedirectHandler() if allow_redirects else YDLNoRedirectHandler()]

        for handler in handlers:
            opener.add_handler(handler)

        # Delete the default user-agent header, which would otherwise apply in
        # cases where our custom HTTP handler doesn't come into play
        # (See https://github.com/ytdl-org/youtube-dl/issues/1309 for details)
        opener.addheaders = []
        return opener

    def get_opener(self, request):
        return self._openers.setdefault(
            frozenset(list(request.proxies.items()) + [request.allow_redirects]),
            self._create_opener(proxies=request.proxies, allow_redirects=request.allow_redirects))

    def _make_sslcontext(self, verify, **kwargs):
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
        return context

    def _real_handle(self, request):
        urllib_req = urllib.request.Request(
            url=request.url, data=request.data, headers=dict(request.headers), method=request.method)

        try:
            res = self.get_opener(request).open(urllib_req, timeout=request.timeout)
        except urllib.error.HTTPError as e:
            if isinstance(e.fp, (http.client.HTTPResponse, urllib.response.addinfourl)):
                raise HTTPError(UrllibHTTPResponseAdapter(e.fp), redirect_loop='redirect error' in str(e))
            raise  # unexpected
        except urllib.error.URLError as e:
            cause = e.reason
            # e.reason may be a string
            if isinstance(cause, Exception):
                handle_sslerror(cause)
                handle_response_read_exceptions(cause)
            raise TransportError(cause=e)

        except Exception as e:
            handle_response_read_exceptions(e)
            raise

        return UrllibHTTPResponseAdapter(res)
