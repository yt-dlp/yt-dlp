from typing import Dict, List

# TODO: all request handlers should be safely imported
from ._urllib import UrllibRH  # noqa: F401
from .common import RequestHandler
from .exceptions import NoSupportingHandlers, RequestError, UnsupportedRequest
from .request import Request
from .response import Response
from ..utils import bug_reports_message


class RequestDirector:
    """RequestDirector class

    Helper class that, when given a request, finds a RequestHandler that supports it.
    """

    def __init__(self, logger=None):
        self._handlers: Dict[RequestHandler] = {}
        self.logger = logger  # TODO: default logger

    def close(self):
        for handler in self._handlers.values():
            handler.close()

    def add_handler(self, handler: RequestHandler):
        """Add a handler. If a handler of the same rh_key exists, it will overwrite it"""
        assert isinstance(handler, RequestHandler)
        self._handlers[handler.rh_key()] = handler

    def remove_handler(self, rh_key):
        self._handlers.pop(rh_key, None)

    def get_handler(self, rh_key):
        """Get a handler instance by rh_key"""
        return self._handlers.get(rh_key)

    def get_handlers(self):
        return list(self._handlers.values())

    def remove_handlers(self):
        self._handlers.clear()

    def send(self, request: Request) -> Response:
        """
        Passes a request onto a suitable RequestHandler
        """
        if len(self._handlers) == 0:
            raise RequestError('No request handlers configured')

        assert isinstance(request, Request)

        unexpected_errors = []
        unsupported_errors = []
        # TODO (future): add a per-request preference system
        for handler in reversed(list(self._handlers.values())):
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
                    f'Unexpected error from "{handler.RH_NAME}" request handler: {type(e).__name__}: {e}' + bug_reports_message(),
                    is_error=False)
                unexpected_errors.append(e)
                continue

            assert isinstance(response, Response)
            return response

        raise NoSupportingHandlers(unsupported_errors, unexpected_errors)


def get_request_handler(key):
    """Get a RequestHandler by its rh_key"""
    return globals()[key + 'RH']


def list_request_handler_classes() -> List[RequestHandler]:
    """List all RequestHandler classes, sorted by name."""
    return sorted(
        (rh for name, rh in globals().items() if name.endswith('RH')),
        key=lambda x: x.RH_NAME.lower())


__all__ = list_request_handler_classes()
__all__.extend(['RequestDirector', 'list_request_handler_classes', 'get_request_handler'])
