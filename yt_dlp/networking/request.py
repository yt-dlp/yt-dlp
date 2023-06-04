from __future__ import annotations

import functools
import io
import typing
import urllib.request
from typing import Union, Iterable, Mapping

from ..utils import extract_basic_auth, escape_url, sanitize_url, update_url_query, CaseInsensitiveDict

_TYPE_REQ_DATA = Union[bytes, typing.Iterable[bytes], typing.IO, None]


class Request:
    """
    Represents a request to be made.
    Partially backwards-compatible with urllib.request.Request.

    @param url: url to send. Will be sanitized and auth will be extracted as basic auth if present.
    @param data: payload data to send. Must be bytes, iterable of bytes, a file-like object or None
    @param headers: headers to send.
    @param proxies: proxy dict mapping of proto:proxy to use for the request and any redirects.
    @param query: URL query parameters to update the url with.
    @param method: HTTP method to use. If no method specified, will use POST if payload data is present else GET
    @param timeout: socket timeout value for this request.

    A Request may also have the following special headers:
    Ytdl-request-proxy: proxy url to use for request.

    Apart from the url protocol, proxy dict also supports the following keys:
    - all: proxy to use for all protocols. Used as a fallback if no proxy is set for a specific protocol.
    - no: comma seperated list of hostnames (optionally with port) to not use a proxy for.

    A proxy value can be set to __noproxy__ or None to set no proxy for that protocol.
    """

    def __init__(
            self,
            url: str,
            data: _TYPE_REQ_DATA = None,
            headers: typing.Mapping = None,
            proxies: dict = None,
            query: dict = None,
            method: str = None,
            timeout: Union[float, int] = None,
    ):

        url, basic_auth_header = extract_basic_auth(escape_url(sanitize_url(url)))

        if query:
            url = update_url_query(url, query)
        # rely on urllib Request's url parsing
        self.__request_store = urllib.request.Request(url)
        self.method = method
        self._headers = CaseInsensitiveDict(headers)
        self._data = None
        self.data = data
        self.timeout = timeout

        if basic_auth_header:
            self.headers['Authorization'] = basic_auth_header

        self.proxies = dict(proxies or {})

    @property
    def url(self):
        return self.__request_store.full_url

    @url.setter
    def url(self, url):
        self.__request_store.full_url = url

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: _TYPE_REQ_DATA):
        # Try catch some common mistakes
        if data is not None and (not isinstance(data, (bytes, io.IOBase, Iterable)) or isinstance(data, (str, Mapping))):
            raise TypeError('data must be bytes, iterable of bytes, or a file-like object')

        # https://docs.python.org/3/library/urllib.request.html#urllib.request.Request.data
        if data != self._data:
            self._data = data
            if 'content-length' in self.headers:
                del self.headers['content-length']

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

    @property
    def method(self):
        return self.__method or ('POST' if self.data is not None else 'GET')

    @method.setter
    def method(self, method: str):
        self.__method = method

    def update(self, url=None, data=None, headers=None, query=None):
        self.data = data or self.data
        self.headers.update(headers or {})
        self.url = update_url_query(url or self.url, query or {})

    def copy(self):
        return type(self)(
            url=self.url, data=self.data, headers=self.headers.copy(), timeout=self.timeout,
            proxies=self.proxies.copy(), method=self.__method)

    @property
    def type(self):
        """URI scheme"""
        return self.__request_store.type

    @property
    def host(self):
        return self.__request_store.host

    # The following methods are for compatability reasons and are deprecated
    @property
    def fullurl(self):
        """Deprecated, use Request.url"""
        return self.url

    @fullurl.setter
    def fullurl(self, url):
        """Deprecated, use Request.url"""
        self.url = url

    def get_full_url(self):
        """Deprecated, use Request.url"""
        return self.url

    def get_method(self):
        """Deprecated, use Request.method"""
        return self.method

    def has_header(self, name):
        """Deprecated, use `name in Request.headers`"""
        return name in self.headers

    def add_header(self, key, value):
        """Deprecated, use Request.headers[key] = value"""
        self._headers[key] = value

    def get_header(self, key, default=None):
        """Deprecated, use Request.headers.get(key, default)"""
        return self._headers.get(key, default)


HEADRequest = functools.partial(Request, method='HEAD')
PUTRequest = functools.partial(Request, method='PUT')
