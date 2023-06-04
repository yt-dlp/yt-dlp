from __future__ import annotations

import functools
import io
import typing
import urllib.request
from typing import Union, Iterable, Mapping
try:
    from urllib.request import _parse_proxy
except ImportError:
    _parse_proxy = None

from ..utils import extract_basic_auth, escape_url, sanitize_url, update_url_query, CaseInsensitiveDict, remove_start

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

        if query:
            url = update_url_query(url, query)
        self.url = url
        # rely on urllib Request's url parsing
        self.method = method
        self._headers = CaseInsensitiveDict(headers)
        self._data = None
        self.data = data
        self.timeout = timeout
        self.proxies = dict(proxies or {})

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: _TYPE_REQ_DATA):
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

    def update(self, url=None, data=None, headers=None, query=None):
        self.data = data or self.data
        self.headers.update(headers or {})
        self.url = update_url_query(url or self.url, query or {})

    def prepare(self, ydl):
        return PreparedRequest(
            url=self.url,
            data=self.data,
            headers=self.headers,
            proxies=self.proxies,
            method=self.method,
            timeout=self.timeout,
            ydl=ydl,
        )


class PreparedRequest:

    def __init__(self, url, ydl, data=None, headers=None, proxies=None, method=None, timeout=None):
        self.ydl = ydl
        self.headers = self._prepare_headers(headers)
        self.url = self._prepare_url(url)
        self.data = self._prepare_data(data)
        self.method = self._prepare_method(method)
        self.timeout = self._prepare_timeout(timeout)
        self.proxies = self._prepare_proxies(proxies)

    def _prepare_timeout(self, timeout):
        return float(timeout or self.ydl.params.get('socket_timeout') or 20)  # do not accept 0

    def _prepare_url(self, url):
        url, basic_auth_header = extract_basic_auth(escape_url(sanitize_url(url)))
        if basic_auth_header:
            self.headers['Authorization'] = basic_auth_header

        # rely on urllib Request's url parsing
        return urllib.request.Request(url).full_url

    def _prepare_proxies(self, proxies):
        proxies = proxies or self.ydl.proxies
        if not isinstance(proxies, dict):
            proxies = {}
        proxies = proxies.copy()

        req_proxy = self.headers.pop('Ytdl-request-proxy', None)
        if req_proxy:
            proxies = {'all': req_proxy}
        for proxy_key, proxy_url in proxies.items():
            if proxy_url == '__noproxy__':  # compat
                proxies[proxy_key] = None
                continue
            if proxy_key == 'no':  # special case
                continue
            if proxy_url is not None and _parse_proxy is not None:
                # Ensure proxies without a scheme are http.
                proxy_scheme = _parse_proxy(proxy_url)[0]
                if proxy_scheme is None:
                    proxies[proxy_key] = 'http://' + remove_start(proxy_url, '//')
        return proxies

    def _prepare_headers(self, headers):
        headers = CaseInsensitiveDict(self.ydl.params.get('http_headers', {}), headers)
        if 'Youtubedl-no-compression' in headers:  # compat
            del headers['Youtubedl-no-compression']
            headers['Accept-Encoding'] = 'identity'
        return headers

    def _prepare_method(self, method):
        # this needs access to data to set method
        return method or ('POST' if self.data is not None else 'GET')

    def _prepare_data(self, data):
        # Try catch some common mistakes
        if data is not None and (
            not isinstance(data, (bytes, io.IOBase, Iterable)) or isinstance(data, (str, Mapping))
        ):
            raise TypeError('data must be bytes, iterable of bytes, or a file-like object')

        # Requests doesn't set content-type if we have already encoded the data, while urllib does.
        # We need to manually set it in this case as many extractors do not.
        if 'content-type' not in self.headers:
            if isinstance(data, (str, bytes)) or hasattr(data, 'read'):
                self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        return data


HEADRequest = functools.partial(Request, method='HEAD')
PUTRequest = functools.partial(Request, method='PUT')
