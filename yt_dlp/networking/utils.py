from __future__ import annotations

import contextlib
import random
import ssl
import sys
import urllib.parse
import urllib.request

import typing

from ..compat import compat_urllib_parse_unquote_plus, compat_urlparse
from ..dependencies import certifi
from ..socks import ProxyType
from ..utils import CaseInsensitiveDict, std_headers, update_url_query

if typing.TYPE_CHECKING:
    from .common import Request
    from http.cookiejar import CookieJar


def random_user_agent():
    _USER_AGENT_TPL = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36'
    _CHROME_VERSIONS = (
        '90.0.4430.212',
        '90.0.4430.24',
        '90.0.4430.70',
        '90.0.4430.72',
        '90.0.4430.85',
        '90.0.4430.93',
        '91.0.4472.101',
        '91.0.4472.106',
        '91.0.4472.114',
        '91.0.4472.124',
        '91.0.4472.164',
        '91.0.4472.19',
        '91.0.4472.77',
        '92.0.4515.107',
        '92.0.4515.115',
        '92.0.4515.131',
        '92.0.4515.159',
        '92.0.4515.43',
        '93.0.4556.0',
        '93.0.4577.15',
        '93.0.4577.63',
        '93.0.4577.82',
        '94.0.4606.41',
        '94.0.4606.54',
        '94.0.4606.61',
        '94.0.4606.71',
        '94.0.4606.81',
        '94.0.4606.85',
        '95.0.4638.17',
        '95.0.4638.50',
        '95.0.4638.54',
        '95.0.4638.69',
        '95.0.4638.74',
        '96.0.4664.18',
        '96.0.4664.45',
        '96.0.4664.55',
        '96.0.4664.93',
        '97.0.4692.20',
    )
    return _USER_AGENT_TPL % random.choice(_CHROME_VERSIONS)


USER_AGENTS = {
    'Safari': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27',
}


# Use make_std_headers() to get a copy of these
_std_headers = CaseInsensitiveDict({
    'User-Agent': random_user_agent(),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
})


def handle_youtubedl_headers(headers):
    filtered_headers = headers

    if 'Youtubedl-no-compression' in filtered_headers:
        filtered_headers = {k: v for k, v in filtered_headers.items() if k.lower() != 'accept-encoding'}
        del filtered_headers['Youtubedl-no-compression']

    return filtered_headers


def ssl_load_certs(context: ssl.SSLContext, params):
    if certifi is not None and 'no-certifi' not in params.get('compat_opts', []):
        context.load_verify_locations(cafile=certifi.where())
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


def socks_create_proxy_args(socks_proxy):
    url_components = compat_urlparse.urlparse(socks_proxy)
    if url_components.scheme.lower() == 'socks5':
        socks_type = ProxyType.SOCKS5
    elif url_components.scheme.lower() in ('socks', 'socks4'):
        socks_type = ProxyType.SOCKS4
    elif url_components.scheme.lower() == 'socks4a':
        socks_type = ProxyType.SOCKS4A

    def unquote_if_non_empty(s):
        if not s:
            return s
        return compat_urllib_parse_unquote_plus(s)
    return {
        'proxytype': socks_type,
        'addr': url_components.hostname,
        'port': url_components.port or 1080,
        'rdns': True,
        'username': unquote_if_non_empty(url_components.username),
        'password': unquote_if_non_empty(url_components.password),
    }


def select_proxy(url, proxies):
    """Unified proxy selector for all backends"""
    if proxies is None:
        proxies = {}
    url_components = urllib.parse.urlparse(url)
    priority = [
        url_components.scheme or 'http',  # prioritise more specific mappings
        'all'
    ]
    return next((proxies[key] for key in priority if key in proxies), None)


# Get a copy of std headers, while also retaining backwards compat with utils.std_headers
# TODO: just make std_headers backwards compat with this
def make_std_headers():
    return CaseInsensitiveDict(_std_headers, std_headers)


def update_request(req: Request, url: str = None, data=None,
                   headers: typing.Mapping = None, query: dict = None):
    """
    Creates a copy of the request and updates relevant fields
    """
    req = req.copy()
    req.data = data or req.data
    req.headers.update(headers or {})
    req.url = update_url_query(url or req.url, query or {})
    return req


def get_cookie_header(req: Request, cookiejar: CookieJar):
    cookie_req = urllib.request.Request(url=req.url)
    cookiejar.add_cookie_header(cookie_req)
    return cookie_req.get_header('Cookie')


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
