from __future__ import annotations

import contextlib
import functools
import socket
import ssl
import sys
import typing
import urllib.parse
import urllib.request

from .exceptions import RequestError, UnsupportedRequest
from ..dependencies import certifi
from ..socks import ProxyType, sockssocket
from ..utils import format_field, traverse_obj

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from ..utils.networking import HTTPHeaderDict


def ssl_load_certs(context: ssl.SSLContext, use_certifi=True):
    if certifi and use_certifi:
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
                    ssl_load_windows_store_certs(context, storename)
            context.set_default_verify_paths()


def ssl_load_windows_store_certs(ssl_context, storename):
    # Code adapted from _load_windows_store_certs in https://github.com/python/cpython/blob/main/Lib/ssl.py
    try:
        certs = [cert for cert, encoding, trust in ssl.enum_certificates(storename)
                 if encoding == 'x509_asn' and (
                     trust is True or ssl.Purpose.SERVER_AUTH.oid in trust)]
    except PermissionError:
        return
    for cert in certs:
        with contextlib.suppress(ssl.SSLError):
            ssl_context.load_verify_locations(cadata=cert)


def make_socks_proxy_opts(socks_proxy):
    url_components = urllib.parse.urlparse(socks_proxy)
    if url_components.scheme.lower() == 'socks5':
        socks_type = ProxyType.SOCKS5
        rdns = False
    elif url_components.scheme.lower() == 'socks5h':
        socks_type = ProxyType.SOCKS5
        rdns = True
    elif url_components.scheme.lower() == 'socks4':
        socks_type = ProxyType.SOCKS4
        rdns = False
    elif url_components.scheme.lower() == 'socks4a':
        socks_type = ProxyType.SOCKS4A
        rdns = True
    else:
        raise ValueError(f'Unknown SOCKS proxy version: {url_components.scheme.lower()}')

    def unquote_if_non_empty(s):
        if not s:
            return s
        return urllib.parse.unquote_plus(s)
    return {
        'proxytype': socks_type,
        'addr': url_components.hostname,
        'port': url_components.port or 1080,
        'rdns': rdns,
        'username': unquote_if_non_empty(url_components.username),
        'password': unquote_if_non_empty(url_components.password),
    }


def select_proxy(url, proxies):
    """Unified proxy selector for all backends"""
    url_components = urllib.parse.urlparse(url)
    if 'no' in proxies:
        hostport = url_components.hostname + format_field(url_components.port, None, ':%s')
        if urllib.request.proxy_bypass_environment(hostport, {'no': proxies['no']}):
            return
        elif urllib.request.proxy_bypass(hostport):  # check system settings
            return

    return traverse_obj(proxies, url_components.scheme or 'http', 'all')


def get_redirect_method(method, status):
    """Unified redirect method handling"""

    # A 303 must either use GET or HEAD for subsequent request
    # https://datatracker.ietf.org/doc/html/rfc7231#section-6.4.4
    if status == 303 and method != 'HEAD':
        method = 'GET'
    # 301 and 302 redirects are commonly turned into a GET from a POST
    # for subsequent requests by browsers, so we'll do the same.
    # https://datatracker.ietf.org/doc/html/rfc7231#section-6.4.2
    # https://datatracker.ietf.org/doc/html/rfc7231#section-6.4.3
    if status in (301, 302) and method == 'POST':
        method = 'GET'
    return method


def make_ssl_context(
    verify=True,
    client_certificate=None,
    client_certificate_key=None,
    client_certificate_password=None,
    legacy_support=False,
    use_certifi=True,
):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = verify
    context.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE

    # Some servers may reject requests if ALPN extension is not sent. See:
    # https://github.com/python/cpython/issues/85140
    # https://github.com/yt-dlp/yt-dlp/issues/3878
    with contextlib.suppress(NotImplementedError):
        context.set_alpn_protocols(['http/1.1'])
    if verify:
        ssl_load_certs(context, use_certifi)

    if legacy_support:
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

    if client_certificate:
        try:
            context.load_cert_chain(
                client_certificate, keyfile=client_certificate_key,
                password=client_certificate_password)
        except ssl.SSLError:
            raise RequestError('Unable to load client certificate')

        if getattr(context, 'post_handshake_auth', None) is not None:
            context.post_handshake_auth = True
    return context


class InstanceStoreMixin:
    def __init__(self, **kwargs):
        self.__instances = []
        super().__init__(**kwargs)  # So that both MRO works

    @staticmethod
    def _create_instance(**kwargs):
        raise NotImplementedError

    def _get_instance(self, **kwargs):
        for key, instance in self.__instances:
            if key == kwargs:
                return instance

        instance = self._create_instance(**kwargs)
        self.__instances.append((kwargs, instance))
        return instance

    def _close_instance(self, instance):
        if callable(getattr(instance, 'close', None)):
            instance.close()

    def _clear_instances(self):
        for _, instance in self.__instances:
            self._close_instance(instance)
        self.__instances.clear()


def add_accept_encoding_header(headers: HTTPHeaderDict, supported_encodings: Iterable[str]):
    if 'Accept-Encoding' not in headers:
        headers['Accept-Encoding'] = ', '.join(supported_encodings) or 'identity'


def wrap_request_errors(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except UnsupportedRequest as e:
            if e.handler is None:
                e.handler = self
            raise
    return wrapper


def _socket_connect(ip_addr, timeout, source_address):
    af, socktype, proto, canonname, sa = ip_addr
    sock = socket.socket(af, socktype, proto)
    try:
        if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(timeout)
        if source_address:
            sock.bind(source_address)
        sock.connect(sa)
        return sock
    except socket.error:
        sock.close()
        raise


def create_socks_proxy_socket(dest_addr, proxy_args, proxy_ip_addr, timeout, source_address):
    af, socktype, proto, canonname, sa = proxy_ip_addr
    sock = sockssocket(af, socktype, proto)
    try:
        connect_proxy_args = proxy_args.copy()
        connect_proxy_args.update({'addr': sa[0], 'port': sa[1]})
        sock.setproxy(**connect_proxy_args)
        if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:  # noqa: E721
            sock.settimeout(timeout)
        if source_address:
            sock.bind(source_address)
        sock.connect(dest_addr)
        return sock
    except socket.error:
        sock.close()
        raise


def create_connection(
    address,
    timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address=None,
    *,
    _create_socket_func=_socket_connect
):
    # Work around socket.create_connection() which tries all addresses from getaddrinfo() including IPv6.
    # This filters the addresses based on the given source_address.
    # Based on: https://github.com/python/cpython/blob/main/Lib/socket.py#L810
    host, port = address
    ip_addrs = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    if not ip_addrs:
        raise socket.error('getaddrinfo returns an empty list')
    if source_address is not None:
        af = socket.AF_INET if ':' not in source_address[0] else socket.AF_INET6
        ip_addrs = [addr for addr in ip_addrs if addr[0] == af]
        if not ip_addrs:
            raise OSError(
                f'No remote IPv{4 if af == socket.AF_INET else 6} addresses available for connect. '
                f'Can\'t use "{source_address[0]}" as source address')

    err = None
    for ip_addr in ip_addrs:
        try:
            sock = _create_socket_func(ip_addr, timeout, source_address)
            # Explicitly break __traceback__ reference cycle
            # https://bugs.python.org/issue36820
            err = None
            return sock
        except socket.error as e:
            err = e

    try:
        raise err
    finally:
        # Explicitly break __traceback__ reference cycle
        # https://bugs.python.org/issue36820
        err = None
