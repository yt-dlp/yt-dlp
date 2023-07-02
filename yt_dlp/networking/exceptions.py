from __future__ import annotations

import http.client
import typing
import urllib.error
import urllib.response

from ..utils import YoutubeDLError, AutoCloseMixin

if typing.TYPE_CHECKING:
    from .common import RequestHandler, Response


class RequestError(YoutubeDLError):
    def __init__(
        self,
        msg: str = None,
        cause: Exception | str | None = None,
        handler: RequestHandler = None
    ):
        self.handler = handler
        self.cause = cause
        if not msg and cause:
            msg = str(cause)
        super().__init__(msg)


class UnsupportedRequest(RequestError):
    """raised when a handler cannot handle a request"""
    pass


class NoSupportingHandlers(RequestError):
    """raised when no handlers can support a request for various reasons"""

    def __init__(self, unsupported_errors: list[UnsupportedRequest], unexpected_errors: list[Exception]):
        self.unsupported_errors = unsupported_errors or []
        self.unexpected_errors = unexpected_errors or []

        # Print a quick summary of the errors
        err_handler_map = {}
        for err in unsupported_errors:
            err_handler_map.setdefault(err.msg, []).append(err.handler.RH_NAME)

        reason_str = ', '.join([f'{msg} ({", ".join(handlers)})' for msg, handlers in err_handler_map.items()])
        if unexpected_errors:
            reason_str = ' + '.join(filter(None, [reason_str, f'{len(unexpected_errors)} unexpected error(s)']))

        err_str = 'Unable to handle request'
        if reason_str:
            err_str += f': {reason_str}'

        super().__init__(msg=err_str)


class TransportError(RequestError):
    """Network related errors"""


class HTTPError(RequestError, AutoCloseMixin):
    def __init__(self, response: Response, redirect_loop=False):
        self.response = response
        self.headers = response.headers
        self.status = response.status
        self.url = response.url
        self.reason = response.reason

        msg = f'HTTP Error {response.status}: {response.reason}'
        if redirect_loop:
            msg += ' (redirect loop detected)'

        super().__init__(msg=msg)

    def close(self):
        self.response.close()


class CompatHTTPError(urllib.error.HTTPError, HTTPError):
    def __init__(self, httperror: HTTPError):
        super().__init__(url=httperror.url, code=httperror.status, msg=httperror.msg[len(f'HTTP Error {httperror.status}: '):], hdrs=httperror.headers, fp=httperror.response)
        # Don't close the underlying HTTP Error when this adapter is closed.
        # It can handle closing itself. This is for the case that the http error is used elsewhere.
        self._closer.file = None
        self._http_error = httperror  # keep ref

    # def __getattribute__(self, item):
    #     COMPAT_MAP = {
    #         'code': 'status',
    #         'hdrs': 'headers',
    #         'info': 'headers',
    #         'getcode': 'status',
    #         'geturl': 'url',
    #         'filename': 'url',
    #         'read': 'response.read',
    #         'fp': 'response',
    #     }
    #     if item in COMPAT_MAP:
    #         warnings.warn(f'HTTPError.{item} is deprecated, use HTTPError.{COMPAT_MAP[item]} instead', DeprecationWarning)
    #     return super().__getattribute__(item)


# Backwards compat with http.client.IncompleteRead
class IncompleteRead(TransportError, http.client.IncompleteRead):
    def __init__(self, partial, cause=None, expected=None):
        self.partial = partial
        self.expected = expected
        super().__init__(msg=repr(self), cause=cause)
        http.client.IncompleteRead.__init__(self, partial=partial, expected=expected)


class SSLError(TransportError):
    pass


class ProxyError(TransportError):
    pass


network_exceptions = (HTTPError, TransportError)
