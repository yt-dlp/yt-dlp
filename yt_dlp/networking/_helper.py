from __future__ import annotations

import contextlib
import ssl
import sys
import urllib.parse

from ..dependencies import certifi
from ..socks import ProxyType
from ..utils import YoutubeDLError


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
                    _ssl_load_windows_store_certs(context, storename)
            context.set_default_verify_paths()


def _ssl_load_windows_store_certs(ssl_context, storename):
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
    elif url_components.scheme.lower() in ('socks', 'socks4'):
        socks_type = ProxyType.SOCKS4
    elif url_components.scheme.lower() == 'socks4a':
        socks_type = ProxyType.SOCKS4A

    def unquote_if_non_empty(s):
        if not s:
            return s
        return urllib.parse.unquote_plus(s)
    return {
        'proxytype': socks_type,
        'addr': url_components.hostname,
        'port': url_components.port or 1080,
        'rdns': True,
        'username': unquote_if_non_empty(url_components.username),
        'password': unquote_if_non_empty(url_components.password),
    }


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
            raise YoutubeDLError('Unable to load client certificate')

    return context


def add_accept_encoding_header(headers, supported_encodings):
    if supported_encodings and 'Accept-Encoding' not in headers:
        headers['Accept-Encoding'] = ', '.join(supported_encodings)

    elif 'Accept-Encoding' not in headers:
        headers['Accept-Encoding'] = 'identity'
