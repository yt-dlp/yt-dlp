from __future__ import annotations

import typing

from ..utils import YoutubeDLError

if typing.TYPE_CHECKING:
    from .common import RequestHandler, Response


class RequestError(YoutubeDLError):
    def __init__(
        self,
        msg: str | None = None,
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


class HTTPError(RequestError):
    def __init__(self, response: Response, redirect_loop=False):
        self.response = response
        self.status = response.status
        self.reason = response.reason
        self.redirect_loop = redirect_loop
        msg = f'HTTP Error {response.status}: {response.reason}'
        if redirect_loop:
            msg += ' (redirect loop detected)'

        super().__init__(msg=msg)

    def close(self):
        self.response.close()

    def __repr__(self):
        return f'<HTTPError {self.status}: {self.reason}>'


class IncompleteRead(TransportError):
    def __init__(self, partial: int, expected: int | None = None, **kwargs):
        self.partial = partial
        self.expected = expected
        msg = f'{partial} bytes read'
        if expected is not None:
            msg += f', {expected} more expected'

        super().__init__(msg=msg, **kwargs)

    def __repr__(self):
        return f'<IncompleteRead: {self.msg}>'


class SSLError(TransportError):
    pass


class CertificateVerifyError(SSLError):
    """Raised when certificate validated has failed"""
    pass


class ProxyError(TransportError):
    pass


network_exceptions = (HTTPError, TransportError)
