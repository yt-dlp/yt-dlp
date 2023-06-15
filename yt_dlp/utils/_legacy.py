"""No longer used and new code should not use. Exists only for API compat."""
import contextlib
import platform
import struct
import sys
import urllib.parse
import zlib
import urllib.request
import http.client
import functools
import urllib.error
import socket

from ._utils import decode_base_n, preferredencoding, YoutubeDLError
from .traversal import traverse_obj
from ..dependencies import certifi, websockets
import ssl
from ..cookies import YoutubeDLCookieJar  # noqa: F401
from ..networking._urllib import (  # noqa: F401
    PUTRequest,
    HEADRequest,
    make_socks_conn_class,
    RedirectHandler as YoutubeDLRedirectHandler,
    update_Request,
    HTTPHandler as YoutubeDLHandler,
    SUPPORTED_ENCODINGS,
)
from ..networking.utils import random_user_agent, _ssl_load_windows_store_certs, std_headers  # noqa: F401
from ..networking.exceptions import network_exceptions, HTTPError  # noqa: F401
from ..socks import ProxyType, sockssocket   # noqa: F401

has_certifi = bool(certifi)
has_websockets = bool(websockets)


def load_plugins(name, suffix, namespace):
    from ..plugins import load_plugins
    ret = load_plugins(name, suffix)
    namespace.update(ret)
    return ret


def traverse_dict(dictn, keys, casesense=True):
    return traverse_obj(dictn, keys, casesense=casesense, is_user_input=True, traverse_string=True)


def decode_base(value, digits):
    return decode_base_n(value, table=digits)


def platform_name():
    """ Returns the platform name as a str """
    return platform.platform()


def get_subprocess_encoding():
    if sys.platform == 'win32' and sys.getwindowsversion()[0] >= 5:
        # For subprocess calls, encode with locale encoding
        # Refer to http://stackoverflow.com/a/9951851/35070
        encoding = preferredencoding()
    else:
        encoding = sys.getfilesystemencoding()
    if encoding is None:
        encoding = 'utf-8'
    return encoding


# UNUSED
# Based on png2str() written by @gdkchan and improved by @yokrysty
# Originally posted at https://github.com/ytdl-org/youtube-dl/issues/9706
def decode_png(png_data):
    # Reference: https://www.w3.org/TR/PNG/
    header = png_data[8:]

    if png_data[:8] != b'\x89PNG\x0d\x0a\x1a\x0a' or header[4:8] != b'IHDR':
        raise OSError('Not a valid PNG file.')

    int_map = {1: '>B', 2: '>H', 4: '>I'}
    unpack_integer = lambda x: struct.unpack(int_map[len(x)], x)[0]

    chunks = []

    while header:
        length = unpack_integer(header[:4])
        header = header[4:]

        chunk_type = header[:4]
        header = header[4:]

        chunk_data = header[:length]
        header = header[length:]

        header = header[4:]  # Skip CRC

        chunks.append({
            'type': chunk_type,
            'length': length,
            'data': chunk_data
        })

    ihdr = chunks[0]['data']

    width = unpack_integer(ihdr[:4])
    height = unpack_integer(ihdr[4:8])

    idat = b''

    for chunk in chunks:
        if chunk['type'] == b'IDAT':
            idat += chunk['data']

    if not idat:
        raise OSError('Unable to read PNG data.')

    decompressed_data = bytearray(zlib.decompress(idat))

    stride = width * 3
    pixels = []

    def _get_pixel(idx):
        x = idx % stride
        y = idx // stride
        return pixels[y][x]

    for y in range(height):
        basePos = y * (1 + stride)
        filter_type = decompressed_data[basePos]

        current_row = []

        pixels.append(current_row)

        for x in range(stride):
            color = decompressed_data[1 + basePos + x]
            basex = y * stride + x
            left = 0
            up = 0

            if x > 2:
                left = _get_pixel(basex - 3)
            if y > 0:
                up = _get_pixel(basex - stride)

            if filter_type == 1:  # Sub
                color = (color + left) & 0xff
            elif filter_type == 2:  # Up
                color = (color + up) & 0xff
            elif filter_type == 3:  # Average
                color = (color + ((left + up) >> 1)) & 0xff
            elif filter_type == 4:  # Paeth
                a = left
                b = up
                c = 0

                if x > 2 and y > 0:
                    c = _get_pixel(basex - stride - 3)

                p = a + b - c

                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)

                if pa <= pb and pa <= pc:
                    color = (color + a) & 0xff
                elif pb <= pc:
                    color = (color + b) & 0xff
                else:
                    color = (color + c) & 0xff

            current_row.append(color)

    return width, height, pixels


def register_socks_protocols():
    # "Register" SOCKS protocols
    # In Python < 2.6.5, urlsplit() suffers from bug https://bugs.python.org/issue7904
    # URLs with protocols not in urlparse.uses_netloc are not handled correctly
    for scheme in ('socks', 'socks4', 'socks4a', 'socks5'):
        if scheme not in urllib.parse.uses_netloc:
            urllib.parse.uses_netloc.append(scheme)


def handle_youtubedl_headers(headers):
    filtered_headers = headers

    if 'Youtubedl-no-compression' in filtered_headers:
        filtered_headers = {k: v for k, v in filtered_headers.items() if k.lower() != 'accept-encoding'}
        del filtered_headers['Youtubedl-no-compression']

    return filtered_headers


def request_to_url(req):
    if isinstance(req, urllib.request.Request):
        return req.get_full_url()
    else:
        return req


def sanitized_Request(url, *args, **kwargs):
    from ..utils import extract_basic_auth, escape_url, sanitize_url
    url, auth_header = extract_basic_auth(escape_url(sanitize_url(url)))
    if auth_header is not None:
        headers = args[1] if len(args) >= 2 else kwargs.setdefault('headers', {})
        headers['Authorization'] = auth_header
    return urllib.request.Request(url, *args, **kwargs)


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


class YoutubeDLHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, params, https_conn_class=None, *args, **kwargs):
        urllib.request.HTTPSHandler.__init__(self, *args, **kwargs)
        self._https_conn_class = https_conn_class or http.client.HTTPSConnection
        self._params = params

    def https_open(self, req):
        kwargs = {}
        conn_class = self._https_conn_class

        if hasattr(self, '_context'):  # python > 2.6
            kwargs['context'] = self._context
        if hasattr(self, '_check_hostname'):  # python 3.x
            kwargs['check_hostname'] = self._check_hostname

        socks_proxy = req.headers.get('Ytdl-socks-proxy')
        if socks_proxy:
            conn_class = make_socks_conn_class(conn_class, socks_proxy)
            del req.headers['Ytdl-socks-proxy']

        try:
            return self.do_open(
                functools.partial(_create_http_connection, self, conn_class, True), req, **kwargs)
        except urllib.error.URLError as e:
            if (isinstance(e.reason, ssl.SSLError)
                    and getattr(e.reason, 'reason', None) == 'SSLV3_ALERT_HANDSHAKE_FAILURE'):
                raise YoutubeDLError('SSLV3_ALERT_HANDSHAKE_FAILURE: Try using --legacy-server-connect')
            raise


class YoutubeDLCookieProcessor(urllib.request.HTTPCookieProcessor):
    def __init__(self, cookiejar=None):
        urllib.request.HTTPCookieProcessor.__init__(self, cookiejar)

    def http_response(self, request, response):
        return urllib.request.HTTPCookieProcessor.http_response(self, request, response)

    https_request = urllib.request.HTTPCookieProcessor.http_request
    https_response = http_response


def make_HTTPS_handler(params, **kwargs):
    opts_check_certificate = not params.get('nocheckcertificate')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = opts_check_certificate
    if params.get('legacyserverconnect'):
        context.options |= 4  # SSL_OP_LEGACY_SERVER_CONNECT
        # Allow use of weaker ciphers in Python 3.10+. See https://bugs.python.org/issue43998
        context.set_ciphers('DEFAULT')
    elif (
        sys.version_info < (3, 10)
        and ssl.OPENSSL_VERSION_INFO >= (1, 1, 1)
        and not ssl.OPENSSL_VERSION.startswith('LibreSSL')
    ):
        # Backport the default SSL ciphers and minimum TLS version settings from Python 3.10 [1].
        # This is to ensure consistent behavior across Python versions, and help avoid fingerprinting
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
        context.set_ciphers('@SECLEVEL=2:ECDH+AESGCM:ECDH+CHACHA20:ECDH+AES:DHE+AES:!aNULL:!eNULL:!aDSS:!SHA1:!AESCCM')
        context.minimum_version = ssl.TLSVersion.TLSv1_2

    context.verify_mode = ssl.CERT_REQUIRED if opts_check_certificate else ssl.CERT_NONE
    if opts_check_certificate:
        if has_certifi and 'no-certifi' not in params.get('compat_opts', []):
            context.load_verify_locations(cafile=certifi.where())
        else:
            try:
                context.load_default_certs()
                # Work around the issue in load_default_certs when there are bad certificates. See:
                # https://github.com/yt-dlp/yt-dlp/issues/1060,
                # https://bugs.python.org/issue35665, https://bugs.python.org/issue45312
            except ssl.SSLError:
                # enum_certificates is not present in mingw python. See https://github.com/yt-dlp/yt-dlp/issues/1151
                if sys.platform == 'win32' and hasattr(ssl, 'enum_certificates'):
                    for storename in ('CA', 'ROOT'):
                        _ssl_load_windows_store_certs(context, storename)
                context.set_default_verify_paths()

    client_certfile = params.get('client_certificate')
    if client_certfile:
        try:
            context.load_cert_chain(
                client_certfile, keyfile=params.get('client_certificate_key'),
                password=params.get('client_certificate_password'))
        except ssl.SSLError:
            raise YoutubeDLError('Unable to load client certificate')

    # Some servers may reject requests if ALPN extension is not sent. See:
    # https://github.com/python/cpython/issues/85140
    # https://github.com/yt-dlp/yt-dlp/issues/3878
    with contextlib.suppress(NotImplementedError):
        context.set_alpn_protocols(['http/1.1'])

    return YoutubeDLHTTPSHandler(params, context=context, **kwargs)


class PerRequestProxyHandler(urllib.request.ProxyHandler):
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
