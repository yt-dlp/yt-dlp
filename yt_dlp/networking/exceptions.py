from __future__ import annotations

import http.client
import urllib.error

from ..utils import YoutubeDLError
import typing
if typing.TYPE_CHECKING:
    from .response import Response
    from . import RequestHandler
    from typing import List, Union


class RequestError(YoutubeDLError):
    def __init__(
        self,
        msg: str = None,
        cause: Union[Exception, str, None] = None,
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
    def __init__(self, unsupported_errors: List[UnsupportedRequest], unexpected_errors: List[Exception]):
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


# Backwards compat with urllib.error.HTTPError
class HTTPError(urllib.error.HTTPError, RequestError):
    def __init__(self, response: Response, redirect_loop=False):
        self.response = response
        msg = response.reason or ''
        if redirect_loop:
            msg += ' (redirect loop detected)'
        RequestError.__init__(self)
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
    pass


class ProxyError(TransportError):
    pass


network_exceptions = (HTTPError, TransportError)
