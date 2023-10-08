from __future__ import annotations

import typing
import urllib.error

from ..utils import YoutubeDLError, deprecation_warning

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
    def __init__(self, partial: int, expected: int = None, **kwargs):
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


class _CompatHTTPError(urllib.error.HTTPError, HTTPError):
    """
    Provides backwards compatibility with urllib.error.HTTPError.
    Do not use this class directly, use HTTPError instead.
    """

    def __init__(self, http_error: HTTPError):
        super().__init__(
            url=http_error.response.url,
            code=http_error.status,
            msg=http_error.msg,
            hdrs=http_error.response.headers,
            fp=http_error.response
        )
        self._closer.close_called = True  # Disable auto close
        self._http_error = http_error
        HTTPError.__init__(self, http_error.response, redirect_loop=http_error.redirect_loop)

    @property
    def status(self):
        return self._http_error.status

    @status.setter
    def status(self, value):
        return

    @property
    def reason(self):
        return self._http_error.reason

    @reason.setter
    def reason(self, value):
        return

    @property
    def headers(self):
        deprecation_warning('HTTPError.headers is deprecated, use HTTPError.response.headers instead')
        return self._http_error.response.headers

    @headers.setter
    def headers(self, value):
        return

    def info(self):
        deprecation_warning('HTTPError.info() is deprecated, use HTTPError.response.headers instead')
        return self.response.headers

    def getcode(self):
        deprecation_warning('HTTPError.getcode is deprecated, use HTTPError.status instead')
        return self.status

    def geturl(self):
        deprecation_warning('HTTPError.geturl is deprecated, use HTTPError.response.url instead')
        return self.response.url

    @property
    def code(self):
        deprecation_warning('HTTPError.code is deprecated, use HTTPError.status instead')
        return self.status

    @code.setter
    def code(self, value):
        return

    @property
    def url(self):
        deprecation_warning('HTTPError.url is deprecated, use HTTPError.response.url instead')
        return self.response.url

    @url.setter
    def url(self, value):
        return

    @property
    def hdrs(self):
        deprecation_warning('HTTPError.hdrs is deprecated, use HTTPError.response.headers instead')
        return self.response.headers

    @hdrs.setter
    def hdrs(self, value):
        return

    @property
    def filename(self):
        deprecation_warning('HTTPError.filename is deprecated, use HTTPError.response.url instead')
        return self.response.url

    @filename.setter
    def filename(self, value):
        return

    def __getattr__(self, name):
        # File operations are passed through the response.
        # Warn for some commonly used ones
        passthrough_warnings = {
            'read': 'response.read()',
            # technically possibly due to passthrough, but we should discourage this
            'get_header': 'response.get_header()',
            'readable': 'response.readable()',
            'closed': 'response.closed',
            'tell': 'response.tell()',
        }
        if name in passthrough_warnings:
            deprecation_warning(f'HTTPError.{name} is deprecated, use HTTPError.{passthrough_warnings[name]} instead')
        return super().__getattr__(name)

    def __str__(self):
        return str(self._http_error)

    def __repr__(self):
        return repr(self._http_error)


network_exceptions = (HTTPError, TransportError)
