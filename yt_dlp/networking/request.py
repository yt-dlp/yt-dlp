from __future__ import annotations

import copy
import functools
import io
import typing
import urllib.request
from http.cookiejar import CookieJar
from typing import Union, Iterable, Mapping
try:
    from urllib.request import _parse_proxy
except ImportError:
    _parse_proxy = None

from ..utils import escape_url, sanitize_url, update_url_query, CaseInsensitiveDict

_TYPE_REQ_DATA = Union[bytes, typing.Iterable[bytes], typing.IO, None]


class Request:
    """
    Represents a request to be made.
    Partially backwards-compatible with urllib.request.Request.

    @param url: url to send. Will be sanitized.
    @param data: payload data to send. Must be bytes, iterable of bytes, a file-like object or None
    @param headers: headers to send.
    @param proxies: proxy dict mapping of proto:proxy to use for the request and any redirects.
    @param query: URL query parameters to update the url with.
    @param method: HTTP method to use. If no method specified, will use POST if payload data is present else GET
    @param extensions:
    @param timeout: socket timeout value for this request. Sets the timeout extension.
    @param cookiejar: Cookiejar to use for this request. Sets the cookiejar extension.

    Apart from the url protocol, proxy dict also supports the following keys:
    - all: proxy to use for all protocols. Used as a fallback if no proxy is set for a specific protocol.
    - no: comma seperated list of hostnames (optionally with port) to not use a proxy for.

    """

    def __init__(
            self,
            url: str,
            data: _TYPE_REQ_DATA = None,
            headers: typing.Mapping = None,
            proxies: dict = None,
            query: dict = None,
            method: str = None,
            extensions: dict = None,
            timeout: Union[float, int] = None,
            cookiejar: CookieJar = None
    ):

        self._headers = CaseInsensitiveDict()
        self._data = None

        if query:
            url = update_url_query(url, query)

        self.url = url
        self.method = method
        self.data = data
        if headers:
            self.headers = headers  # XXX: must be done after setting data

        self.proxies = proxies or {}
        self.extensions = extensions or {}

        if timeout:
            self.extensions['timeout'] = timeout
        if cookiejar:
            self.extensions['cookiejar'] = cookiejar

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = escape_url(sanitize_url(url))

    @property
    def method(self):
        return self._method or ('POST' if self.data is not None else 'GET')

    @method.setter
    def method(self, method):
        if method is None:
            self._method = None
        elif isinstance(method, str):
            self._method = method.upper()
        else:
            raise TypeError('method must be a string')

    @property
    def data(self):
        return self._data

    @property
    def proxies(self):
        return self._proxies

    @proxies.setter
    def proxies(self, proxies):
        if not isinstance(proxies, dict):
            raise TypeError('proxies must be of type dict')
        self._proxies = proxies

    @property
    def extensions(self):
        return self._extensions

    @extensions.setter
    def extensions(self, extensions):
        if not isinstance(extensions, dict):
            raise TypeError('extensions must be of type dict')
        self._extensions = extensions

    @data.setter
    def data(self, data: _TYPE_REQ_DATA):
        # Try catch some common mistakes
        if data is not None and (
            not isinstance(data, (bytes, io.IOBase, Iterable)) or isinstance(data, (str, Mapping))
        ):
            raise TypeError('data must be bytes, iterable of bytes, or a file-like object')

        # https://docs.python.org/3/library/urllib.request.html#urllib.request.Request.data
        if data and data != self._data:
            self._data = data
            if 'Content-Length' in self.headers:
                del self.headers['Content-Length']

            if 'Content-Type' not in self.headers:
                if isinstance(data, (str, bytes)) or hasattr(data, 'read'):
                    self.headers['Content-Type'] = 'application/x-www-form-urlencoded'

        elif data is None:
            self.headers.pop('Content-Length', None)
            self.headers.pop('Content-Type', None)

    @property
    def headers(self) -> CaseInsensitiveDict:
        return self._headers

    @headers.setter
    def headers(self, new_headers: Mapping):
        """Replaces headers of the request. If not a CaseInsensitiveDict, it will be converted to one."""
        if isinstance(new_headers, CaseInsensitiveDict):
            self._headers = new_headers
        elif isinstance(new_headers, Mapping):
            self._headers = CaseInsensitiveDict(new_headers)
        else:
            raise TypeError('headers must be a mapping')

    def update(self, url=None, data=None, headers=None, query=None):
        self.data = data or self.data
        self.headers.update(headers or {})
        self.url = update_url_query(url or self.url, query or {})

    def copy(self):
        return copy.deepcopy(self)


HEADRequest = functools.partial(Request, method='HEAD')
PUTRequest = functools.partial(Request, method='PUT')
