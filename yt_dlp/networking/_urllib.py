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

from ._helper import (
    add_accept_encoding_header,
    get_redirect_method,
    make_socks_proxy_opts,
)
from ..dependencies import brotli
from ..socks import sockssocket
from ..utils import escape_url, update_url_query
from ..utils.networking import clean_headers, std_headers

SUPPORTED_ENCODINGS = ['gzip', 'deflate']

if brotli:
    SUPPORTED_ENCODINGS.append('br')


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


class HTTPHandler(urllib.request.HTTPHandler):
    """Handler for HTTP requests and responses.

    This class, when installed with an OpenerDirector, automatically adds
    the standard headers to every HTTP request and handles gzipped, deflated and
    brotli responses from web servers.

    Part of this code was copied from:

    http://techknack.net/python-urllib2-handlers/

    Andrew Rowls, the author of that code, agreed to release it to the
    public domain.
    """

    def __init__(self, params, *args, **kwargs):
        urllib.request.HTTPHandler.__init__(self, *args, **kwargs)
        self._params = params

    def http_open(self, req):
        conn_class = http.client.HTTPConnection

        socks_proxy = req.headers.get('Ytdl-socks-proxy')
        if socks_proxy:
            conn_class = make_socks_conn_class(conn_class, socks_proxy)
            del req.headers['Ytdl-socks-proxy']

        return self.do_open(functools.partial(
            _create_http_connection, self, conn_class, False),
            req)

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
        gz = gzip.GzipFile(fileobj=io.BytesIO(data), mode='rb')
        try:
            return gz.read()
        except OSError as original_oserror:
            # There may be junk add the end of the file
            # See http://stackoverflow.com/q/4928560/35070 for details
            for i in range(1, 1024):
                try:
                    gz = gzip.GzipFile(fileobj=io.BytesIO(data[:-i]), mode='rb')
                    return gz.read()
                except OSError:
                    continue
            else:
                raise original_oserror

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

        for h, v in self._params.get('http_headers', std_headers).items():
            # Capitalize is needed because of Python bug 2275: http://bugs.python.org/issue2275
            # The dict keys are capitalized because of this bug by urllib
            if h.capitalize() not in req.headers:
                req.add_header(h, v)

        clean_headers(req.headers)
        add_accept_encoding_header(req.headers, SUPPORTED_ENCODINGS)
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
            if isinstance(self.timeout, (int, float)):
                self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))

            if isinstance(self, http.client.HTTPSConnection):
                if hasattr(self, '_context'):  # Python > 2.6
                    self.sock = self._context.wrap_socket(
                        self.sock, server_hostname=self.host)
                else:
                    self.sock = ssl.wrap_socket(self.sock)

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


class ProxyHandler(urllib.request.ProxyHandler):
    def __init__(self, proxies=None):
        # Set default handlers
        for type in ('http', 'https'):
            setattr(self, '%s_open' % type,
                    lambda r, proxy='__noproxy__', type=type, meth=self.proxy_open:
                        meth(r, proxy, type))
        urllib.request.ProxyHandler.__init__(self, proxies)

    def proxy_open(self, req, proxy, type):
        req_proxy = req.headers.get('Ytdl-request-proxy')
        if req_proxy is not None:
            proxy = req_proxy
            del req.headers['Ytdl-request-proxy']

        if proxy == '__noproxy__':
            return None  # No Proxy
        if urllib.parse.urlparse(proxy).scheme.lower() in ('socks', 'socks4', 'socks4a', 'socks5'):
            req.add_header('Ytdl-socks-proxy', proxy)
            # yt-dlp's http/https handlers do wrapping the socket with socks
            return None
        return urllib.request.ProxyHandler.proxy_open(
            self, req, proxy, type)


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
