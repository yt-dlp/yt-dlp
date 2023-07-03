from typing import Dict, List

from ._urllib import UrllibRH  # noqa: F401
from .common import Request, RequestHandler, Response
from .exceptions import NoSupportingHandlers, RequestError, UnsupportedRequest
from ..utils import bug_reports_message


class RequestDirector:
    """RequestDirector class

    Helper class that, when given a request, finds a RequestHandler that supports it.

    @param logger: Logger instance.
    @param verbose: Print debug request information to stdout.
    """

    def __init__(self, logger=None, verbose=False):
        self._handlers: Dict[str, RequestHandler] = {}
        self.logger = logger  # TODO(Grub4k): default logger
        self.verbose = verbose

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

    def print_verbose(self, msg):
        if self.verbose:
            self.logger.to_stdout(f'director: {msg}')

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
            self.print_verbose(f'checking if "{handler.RH_NAME}" request handler supports this request.')
            try:
                handler.validate(request)
            except UnsupportedRequest as e:
                self.print_verbose(
                    f'"{handler.RH_NAME}" request handler cannot handle this request (reason: {type(e).__name__}:{e})')
                unsupported_errors.append(e)
                continue

            self.print_verbose(f'sending request via "{handler.RH_NAME}" request handler.')
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


# TODO(pukkandan): RequestHandler register system for importing
def _get_request_handler(key):
    """Get a RequestHandler by its rh_key"""
    return globals()[key + 'RH']


def _list_request_handler_classes() -> List[RequestHandler]:
    """List all RequestHandler classes, sorted by name."""
    return sorted(
        (rh for name, rh in globals().items() if name.endswith('RH')),
        key=lambda x: x.RH_NAME.lower())


__all__ = _list_request_handler_classes()
__all__.extend(['RequestDirector'])
