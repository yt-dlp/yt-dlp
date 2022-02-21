from __future__ import unicode_literals

import collections
import http.cookiejar
import inspect
import io
import sys
import time
import urllib.parse
from abc import ABC, abstractmethod
from http import HTTPStatus
from email.message import Message
import urllib.request
import urllib.response

from ..compat import compat_cookiejar, compat_str, compat_urllib_request

from ..utils import (
    extract_basic_auth,
    escape_url,
    sanitize_url,
    write_string,
    std_headers,
    update_url_query,
    bug_reports_message, RequestError
)

from .utils import random_user_agent


class Request:
    """
    Request class to define a request to be made.
    A wrapper for urllib.request.Request with improvements for yt-dlp,
    while retaining backwards-compatability where needed (e.g for cookiejar)
    """
    def __init__(
            self, url, data=None, headers=None, proxy=None, compression=True, method=None,
            unverifiable=False, unredirected_headers=None, origin_req_host=None, timeout=None):
        """
        @param proxy: proxy to use for the request, e.g. socks5://127.0.0.1:1080. Default is None.
        @param compression: whether to include content-encoding header on request (i.e. disable/enable compression).
        For everything else, see urllib.request.Request docs: https://docs.python.org/3/library/urllib.request.html?highlight=request#urllib.request.Request
        """
        url, basic_auth_header = extract_basic_auth(escape_url(sanitize_url(url)))
        # Using Request object for url parsing.
        self.__request_store = urllib.request.Request(url, data=data, method=method)
        self._headers = UniqueHTTPHeaderStore(headers)
        self._unredirected_headers = UniqueHTTPHeaderStore(unredirected_headers)
        self.timeout = timeout

        # TODO: add support for passing different types of auth into a YDlRequest, and don't add the headers.
        if basic_auth_header:
            self.unredirected_headers['Authorization'] = basic_auth_header

        self.proxy = proxy
        self.compression = compression

        # See https://docs.python.org/3/library/urllib.request.html#urllib.request.Request
        # and https://datatracker.ietf.org/doc/html/rfc2965.html
        self.unverifiable = unverifiable
        self.origin_req_host = (
            origin_req_host
            or urllib.parse.urlparse(self.url).netloc
            or self.__request_store.origin_req_host)

    @property
    def url(self):
        return self.__request_store.full_url

    @url.setter
    def url(self, url):
        self.__request_store.full_url = url

    @property
    def data(self):
        return self.__request_store.data

    @data.setter
    def data(self, data):
        self.__request_store.data = data

    @property
    def headers(self):
        return self._headers

    @property
    def unredirected_headers(self):
        """Headers to not send in a redirect"""
        return self._unredirected_headers

    @property
    def method(self):
        return self.__request_store.get_method()

    def copy(self):
        return self.__class__(
            self.url, self.data, self.headers.copy(), self.proxy, self.compression, self.method, self.unverifiable,
            self.unredirected_headers.copy())

    """
    The following are backwards compatible functions with urllib.request.Request for cookiejar handling
    """

    def add_unredirected_header(self, key, value):
        self._unredirected_headers.replace_header(key, value)

    def add_header(self, key, value):
        self._headers.replace_header(key, value)

    def has_header(self, header):
        return header in self._headers or header in self._unredirected_headers

    def remove_header(self, key):
        del self._headers[key]
        del self._unredirected_headers[key]

    def get_header(self, key, default=None):
        return self._headers.get(key, self._unredirected_headers.get(key, default))

    def header_items(self):
        return list({**self._unredirected_headers, **self._headers}.items())

    def get_full_url(self):
        return self.url

    def get_method(self):
        return self.method

    @property
    def type(self):
        return self.__request_store.type

    @property
    def host(self):
        return self.__request_store.host


def req_to_ydlreq(req: urllib.request.Request):
    return Request(
        req.get_full_url(), data=req.data, headers=req.headers.copy(), method=req.get_method(),
        unverifiable=req.unverifiable, unredirected_headers=req.unredirected_hdrs.copy(),
        origin_req_host=req.origin_req_host)


class HEADRequest(Request):
    @property
    def method(self):
        return 'HEAD'


class PUTRequest(Request):
    @property
    def method(self):
        return 'PUT'


def update_YDLRequest(req: Request, url=None, data=None, headers=None, query=None):
    """
    Replaces the old update_Request.
    TODO: do we want to replace this with a better method?
    """
    req = req.copy()
    req.data = data or req.data
    req.headers.replace_headers(headers or {})
    req.unredirected_headers.clear()  # these were not copied in update_Request
    req.url = update_url_query(url or req.url, query or {})
    return req


class HTTPResponse(ABC, io.IOBase):
    """
    Adapter interface for responses
    """

    REDIRECT_STATUS_CODES = [301, 302, 303, 307, 308]

    def __init__(self, headers, status, version=None, reason=None):
        self.headers = HTTPHeaderStore(headers)
        self.status = self.code = status
        self.reason = reason
        if not reason:
            try:
                self.reason = HTTPStatus(status).name.replace('_', ' ').title()
            except ValueError:
                pass
        self.version = version  # HTTP Version, e.g. HTTP 1.1 = 11

    def getcode(self):
        return self.status

    @property
    def url(self):
        return self.geturl()

    @abstractmethod
    def geturl(self):
        pass

    def get_redirect_url(self):
        return self.getheader('location') if self.status in self.REDIRECT_STATUS_CODES else None

    def getheaders(self):
        return self.headers

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def info(self):
        return self.headers

    def readable(self):
        return True

    @abstractmethod
    def read(self, amt: int = None):
        raise NotImplementedError


class BackendHandler(ABC):
    """
    Bare-bones backend handler.
    Use this for defining custom protocols for extractors.
    """
    SUPPORTED_PROTOCOLS: list = None

    @classmethod
    def _is_supported_protocol(cls, request: Request):
        return urllib.parse.urlparse(request.url).scheme.lower() in cls.SUPPORTED_PROTOCOLS or []

    def handle(self, request: Request, **req_kwargs):
        """Method to handle given request. Redefine in subclasses"""

    @classmethod
    def can_handle(cls, request: Request, **req_kwargs) -> bool:
        """Validate if handler is suitable for given request. Can override in subclasses."""


class YDLBackendHandler(BackendHandler):
    """Network Backend Handler class
    Responsible for handling requests.

    Backend handlers accept a lot of parameters. In order not to saturate
    the object constructor with arguments, it receives a dictionary of
    options instead.

    Available options:
    cookiejar:          A YoutubeDLCookieJar to store cookies in
    verbose:            Print traffic for debugging to stdout
    """
    params = None

    def __init__(self, ydl, params):
        self.ydl = ydl
        self.params = params or self.params or {}
        self.cookiejar = params.get('cookiejar', http.cookiejar.CookieJar())
        self.print_traffic = bool(self.params.get('verbose'))
        self._initialize()

    def handle(self, request: Request, **req_kwargs):
        return self._real_handle(request, **req_kwargs)

    def to_screen(self, *args, **kwargs):
        self.ydl.to_stdout(*args, **kwargs)

    def to_stderr(self, message):
        self.ydl.to_stderr(message)

    def report_warning(self, *args, **kwargs):
        self.ydl.report_warning(*args, **kwargs)

    def report_error(self, *args, **kwargs):
        self.ydl.report_error(*args, **kwargs)

    def write_debug(self, *args, **kwargs):
        self.ydl.write_debug(*args, **kwargs)

    def can_handle(self, request: Request, **req_kwargs) -> bool:
        """Validate if handler is suitable for given request. Can override in subclasses."""
        return self._is_supported_protocol(request)

    def _initialize(self):
        """Initialization process. Redefine in subclasses."""
        pass

    def _real_handle(self, request: Request, **kwargs) -> HTTPResponse:
        """Real request handling process. Redefine in subclasses"""


class BackendManager:

    def __init__(self, ydl):
        self.handlers = []
        self.ydl = ydl
        self.socket_timeout = float(self.ydl.params.get('socket_timeout') or 20)  # do not accept 0
        self.proxy = self.get_default_proxy()

    def get_default_proxy(self):
        proxies = urllib.request.getproxies()
        return self.ydl.params.get('proxy') or proxies.get('http') or proxies.get('https')

    def add_handler(self, handler: BackendHandler):
        if handler not in self.handlers:
            self.handlers.append(handler)

    def remove_handler(self, handler):
        """
        Remove backend handler(s)
        @param handler: Handler object or handler type.
        Specifying handler type will remove all handlers of that type.
        idea from yt-dlp#1687
        """
        if inspect.isclass(handler):
            finder = lambda x: isinstance(x, handler)
        else:
            finder = lambda x: x is handler
        self.handlers = [x for x in self.handlers if not finder(handler)]

    def urlopen(self, req):
        if isinstance(req, str):
            req = Request(req)

        if isinstance(req, compat_urllib_request.Request):
            self.ydl.deprecation_warning(
                'An urllib.request.Request has been passed to urlopen(). '
                'This is deprecated and may not work in the future. Please use yt_dlp.networking.common.Request instead.')
            req = req_to_ydlreq(req)

        if req.headers.get('Youtubedl-no-compression'):
            req.compression = False
            del req.headers['Youtubedl-no-compression']

        proxy = req.headers.get('Ytdl-request-proxy')
        if proxy:
            del req.headers['Ytdl-request-proxy']

        req.proxy = proxy or req.proxy or self.proxy
        req.timeout = req.timeout or self.socket_timeout

        for handler in reversed(self.handlers):
            if not handler.can_handle(req):
                continue
            res = handler.handle(req)
            if not res:
                self.ydl.report_warning(f'{handler.__class__} handler returned nothing for response' + bug_reports_message())
                continue
            assert isinstance(res, HTTPResponse)
            return res


class HTTPHeaderStore(Message):
    def __init__(self, data=None):
        super().__init__()
        if data is not None:
            self.add_headers(data)

    def add_headers(self, data):
        for k, v in data.items():
            self.add_header(k, v)

    def replace_headers(self, data):
        for k, v in data.items():
            self.replace_header(k, v)

    def add_header(self, _name: str, _value: str, **kwargs):
        return self._add_header(_name, _value, **kwargs)

    def _add_header(self, name, value, **kwargs):
        return super().add_header(name, str(value), **kwargs)

    def replace_header(self, _name: str, _value: str):
        """
        Similar to add_header, but will replace all existing headers of such name if exists.
        Unlike email.Message, will add the header if it does not already exist.
        """
        try:
            return super().replace_header(_name, str(_value))
        except KeyError:
            return self._add_header(_name, _value)

    def clear(self):
        self._headers = []

    def update(self, new_headers):
        self.replace_headers(new_headers)

    def copy(self):
        return self.__class__(self)


class UniqueHTTPHeaderStore(HTTPHeaderStore):
    def add_header(self, *args, **kwargs):
        return self.replace_header(*args, **kwargs)


class YoutubeDLCookieJar(compat_cookiejar.MozillaCookieJar):
    """
    See [1] for cookie file format.
    1. https://curl.haxx.se/docs/http-cookies.html
    """
    _HTTPONLY_PREFIX = '#HttpOnly_'
    _ENTRY_LEN = 7
    _HEADER = '''# Netscape HTTP Cookie File
# This file is generated by yt-dlp.  Do not edit.
'''
    _CookieFileEntry = collections.namedtuple(
        'CookieFileEntry',
        ('domain_name', 'include_subdomains', 'path', 'https_only', 'expires_at', 'name', 'value'))

    def save(self, filename=None, ignore_discard=False, ignore_expires=False):
        """
        Save cookies to a file.
        Most of the code is taken from CPython 3.8 and slightly adapted
        to support cookie files with UTF-8 in both python 2 and 3.
        """
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(compat_cookiejar.MISSING_FILENAME_TEXT)

        # Store session cookies with `expires` set to 0 instead of an empty
        # string
        for cookie in self:
            if cookie.expires is None:
                cookie.expires = 0

        with io.open(filename, 'w', encoding='utf-8') as f:
            f.write(self._HEADER)
            now = time.time()
            for cookie in self:
                if not ignore_discard and cookie.discard:
                    continue
                if not ignore_expires and cookie.is_expired(now):
                    continue
                if cookie.secure:
                    secure = 'TRUE'
                else:
                    secure = 'FALSE'
                if cookie.domain.startswith('.'):
                    initial_dot = 'TRUE'
                else:
                    initial_dot = 'FALSE'
                if cookie.expires is not None:
                    expires = compat_str(cookie.expires)
                else:
                    expires = ''
                if cookie.value is None:
                    # cookies.txt regards 'Set-Cookie: foo' as a cookie
                    # with no name, whereas http.cookiejar regards it as a
                    # cookie with no value.
                    name = ''
                    value = cookie.name
                else:
                    name = cookie.name
                    value = cookie.value
                f.write(
                    '\t'.join([cookie.domain, initial_dot, cookie.path,
                               secure, expires, name, value]) + '\n')

    def load(self, filename=None, ignore_discard=False, ignore_expires=False):
        """Load cookies from a file."""
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(compat_cookiejar.MISSING_FILENAME_TEXT)

        def prepare_line(line):
            if line.startswith(self._HTTPONLY_PREFIX):
                line = line[len(self._HTTPONLY_PREFIX):]
            # comments and empty lines are fine
            if line.startswith('#') or not line.strip():
                return line
            cookie_list = line.split('\t')
            if len(cookie_list) != self._ENTRY_LEN:
                raise compat_cookiejar.LoadError('invalid length %d' % len(cookie_list))
            cookie = self._CookieFileEntry(*cookie_list)
            if cookie.expires_at and not cookie.expires_at.isdigit():
                raise compat_cookiejar.LoadError('invalid expires at %s' % cookie.expires_at)
            return line

        cf = io.StringIO()
        with io.open(filename, encoding='utf-8') as f:
            for line in f:
                try:
                    cf.write(prepare_line(line))
                except compat_cookiejar.LoadError as e:
                    write_string(
                        'WARNING: skipping cookie file entry due to %s: %r\n'
                        % (e, line), sys.stderr)
                    continue
        cf.seek(0)
        self._really_load(cf, filename, ignore_discard, ignore_expires)
        # Session cookies are denoted by either `expires` field set to
        # an empty string or 0. MozillaCookieJar only recognizes the former
        # (see [1]). So we need force the latter to be recognized as session
        # cookies on our own.
        # Session cookies may be important for cookies-based authentication,
        # e.g. usually, when user does not check 'Remember me' check box while
        # logging in on a site, some important cookies are stored as session
        # cookies so that not recognizing them will result in failed login.
        # 1. https://bugs.python.org/issue17164
        for cookie in self:
            # Treat `expires=0` cookies as session cookies
            if cookie.expires == 0:
                cookie.expires = None
                cookie.discard = True


# Use get_std_headers() to get a copy of these
_std_headers = UniqueHTTPHeaderStore({
    'User-Agent': random_user_agent(),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
})


def get_std_headers(supported_encodings=None):
    headers = _std_headers.copy()
    if supported_encodings:
        headers.replace_header('accept-encoding', ', '.join(supported_encodings))
    headers.replace_headers(std_headers)
    return headers


class UnsupportedBackendHandler(YDLBackendHandler):
    def can_handle(self, request, **req_kwargs):
        raise RequestError('This request is not supported')
