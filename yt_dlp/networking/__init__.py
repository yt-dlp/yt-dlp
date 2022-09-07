from __future__ import annotations

import urllib.request
from typing import Union

from ._urllib import UrllibRH
from .common import (
    HEADRequest,
    PUTRequest,
    Request,
    RequestHandler, Response,
)
from .exceptions import RequestError, UnsupportedRequest
from ..utils import CaseInsensitiveDict, bug_reports_message

REQUEST_HANDLERS = [UrllibRH]


class RequestDirector:

    def __init__(self, ydl):
        self._handlers = []
        self.ydl = ydl

    def close(self):
        for handler in self._handlers:
            handler.close()

    def add_handler(self, handler):
        assert isinstance(handler, RequestHandler)
        if handler not in self._handlers:
            self._handlers.append(handler)

    def remove_handler(self, handler):
        """
        Remove a RequestHandler from the broker.
        If a class is provided, all handlers of that class type are removed.
        """
        self._handlers = [h for h in self._handlers if not (type(h) == handler or h is handler)]

    def get_handlers(self, handler=None):
        """Get all handlers for a particular class type"""
        return [h for h in self._handlers if (type(h) == handler or h is handler)]

    def replace_handler(self, handler):
        self.remove_handler(handler)
        self.add_handler(handler)

    def is_supported(self, request: Request):
        """Check if a request can be handled without making any requests"""
        for handler in self._handlers:
            if handler.can_handle(request):
                return True
        return False

    def send(self, request: Union[Request, str, urllib.request.Request]) -> Response:
        """
        Passes a request onto a suitable RequestHandler
        """
        if len(self._handlers) == 0:
            raise RequestError('No request handlers configured')
        if isinstance(request, str):
            request = Request(request)
        elif isinstance(request, urllib.request.Request):
            # compat
            request = Request(
                request.get_full_url(), data=request.data, method=request.get_method(),
                headers=CaseInsensitiveDict(request.headers, request.unredirected_hdrs),
                timeout=request.timeout if hasattr(request, 'timeout') else None)

        assert isinstance(request, Request)

        unexpected_errors = []
        unsupported_errors = []
        for handler in reversed(self._handlers):
            handler_req = request.copy()
            try:
                self.ydl.to_debugtraffic(f'Forwarding request to "{handler.NAME}" request handler')
                response = handler.handle(handler_req)

            except UnsupportedRequest as e:
                self.ydl.to_debugtraffic(
                    f'"{handler.NAME}" request handler cannot handle this request, trying another handler... (cause: {type(e).__name__}:{e})')
                unsupported_errors.append(e)
                continue

            except Exception as e:
                if isinstance(e, RequestError):
                    raise
                # something went very wrong, try fallback to next handler
                self.ydl.report_error(
                    f'Unexpected error from "{handler.NAME}" request handler: {e}' + bug_reports_message(),
                    is_error=False)
                unexpected_errors.append(e)
                continue

            assert isinstance(response, Response)
            return response

        # no handler was able to handle the request, try print some useful info
        # FIXME: this is a bit ugly
        err_handler_map = {}
        for err in unsupported_errors:
            err_handler_map.setdefault(err.msg, []).append(err.handler.NAME)

        reasons = [f'{msg} ({", ".join(handlers)})' for msg, handlers in err_handler_map.items()]
        if unexpected_errors:
            reasons.append(f'{len(unexpected_errors)} unexpected error(s)')

        err_str = 'Unable to handle request'
        if reasons:
            err_str += ', possible reason(s): ' + ', '.join(reasons)

        raise RequestError(err_str)


__all__ = ['UrllibRH', 'REQUEST_HANDLERS', 'Request', 'HEADRequest', 'PUTRequest', 'RequestHandler', 'RequestDirector']
