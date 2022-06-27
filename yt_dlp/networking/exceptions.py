from __future__ import annotations

import http.client
import typing
import urllib.error

from ..utils import YoutubeDLError

if typing.TYPE_CHECKING:
    from .common import Response


class RequestError(YoutubeDLError):
    def __init__(self, msg=None, cause=None, handler=None):
        self.handler = handler
        self.cause = cause
        if not msg and cause:
            msg = str(cause)
        super().__init__(msg)

    def __str__(self):
        return self.msg + (f' (caused by {self.cause.__class__.__name__})' if self.cause else '')


class UnsupportedRequest(RequestError):
    """raised when a handler cannot handle a request"""
    pass


class TransportError(RequestError):
    """Network related errors"""


# Backwards compatible with urllib.error.HTTPError
class HTTPError(urllib.error.HTTPError, RequestError):
    def __init__(self, response: Response, redirect_loop=False):
        self.response = response
        msg = response.reason or ''
        if redirect_loop:
            msg += ' (redirect loop detected)'
        super().__init__(
            url=response.url, code=response.code, msg=msg, hdrs=response.headers, fp=response)


# Backwards compat with http.client.IncompleteRead
class IncompleteRead(TransportError, http.client.IncompleteRead):
    def __init__(self, partial, cause=None, expected=None):
        self.partial = partial
        self.expected = expected
        super().__init__(msg=repr(self), cause=cause)
        http.client.IncompleteRead.__init__(self, partial=partial, expected=expected)


class SSLError(TransportError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for ssl_err_str in ('SSLV3_ALERT_HANDSHAKE_FAILURE', 'UNSAFE_LEGACY_RENEGOTIATION_DISABLED'):
            if ssl_err_str in str(self.msg):
                self.msg = f'{ssl_err_str}: Try using --legacy-server-connect'
                break


class ProxyError(TransportError):
    pass


network_exceptions = (HTTPError, TransportError)
