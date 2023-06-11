from __future__ import annotations

from ._urllib import UrllibRH  # noqa: F401
from .common import (
    RequestHandler,
)
from .response import Response
from .request import Request, PreparedRequest
from .exceptions import RequestError, UnsupportedRequest
from ..utils import bug_reports_message


class RequestDirector:
    def __init__(self, logger):
        self._handlers = []
        self.logger = logger

    def close(self):
        for handler in self._handlers:
            handler.close()

    def add_handler(self, handler):
        """Add a handler. It will be prioritized over existing handlers"""
        assert isinstance(handler, RequestHandler)
        if handler not in self._handlers:
            self._handlers.append(handler)

    def remove_handler(self, handler):
        """
        Remove a RequestHandler.
        If a class is provided, all handlers of that class type are removed.
        """
        self._handlers = [h for h in self._handlers if not (type(h) == handler or h is handler)]

    def get_handlers(self, handler=None):
        """Get all handlers for a particular class type"""
        return [h for h in self._handlers if (type(h) == handler or h is handler)]

    def replace_handler(self, handler):
        self.remove_handler(handler)
        self.add_handler(handler)

    def send(self, request: PreparedRequest) -> Response:
        """
        Passes a request onto a suitable RequestHandler
        """
        if len(self._handlers) == 0:
            raise RequestError('No request handlers configured')

        assert isinstance(request, PreparedRequest)

        unexpected_errors = []
        unsupported_errors = []
        for handler in reversed(self._handlers):
            self.logger.to_debugtraffic(
                f'director: checking if "{handler.RH_NAME}" request handler supports this request.')
            try:
                handler.validate(request)
            except UnsupportedRequest as e:
                self.logger.to_debugtraffic(
                    f'director: "{handler.RH_NAME}" request handler cannot handle this request (reason: {type(e).__name__}:{e})')
                unsupported_errors.append(e)
                continue
            self.logger.to_debugtraffic(f'director: sending request via "{handler.RH_NAME}" request handler.')
            try:
                response = handler.send(request)
            except RequestError:
                raise
            except Exception as e:
                # something went very wrong, try fallback to next handler
                self.logger.report_error(
                    f'Unexpected error from "{handler.RH_NAME}" request handler: {type(e).__name__}:{e}' + bug_reports_message(),
                    is_error=False)
                unexpected_errors.append(e)
                continue

            assert isinstance(response, Response)
            return response

        # no handler was able to handle the request, try print some useful info
        # FIXME: this is a bit ugly
        err_handler_map = {}
        for err in unsupported_errors:
            err_handler_map.setdefault(err.msg, []).append(err.handler.RH_NAME)

        reasons = [f'{msg} ({", ".join(handlers)})' for msg, handlers in err_handler_map.items()]
        if unexpected_errors:
            reasons.append(f'{len(unexpected_errors)} unexpected error(s)')

        err_str = 'Unable to handle request'
        if reasons:
            err_str += ', possible reason(s): ' + ', '.join(reasons)

        raise RequestError(err_str)


def get_request_handler(key):
    """Get a RequestHandler by its rh_key"""
    return globals()[key + 'RH']


def list_request_handler_classes():
    """List all RequestHandler classes, sorted by name."""
    return sorted(
        (rh for name, rh in globals().items() if name.endswith('RH')),
        key=lambda x: x.RH_NAME.lower())


__all__ = list_request_handler_classes()
__all__.extend(['RequestDirector', 'list_request_handler_classes', 'get_request_handler'])
