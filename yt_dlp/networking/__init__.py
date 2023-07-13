from .common import Request, RequestHandler, Response
from .exceptions import NoSupportingHandlers, RequestError, UnsupportedRequest
from ..utils import bug_reports_message, error_to_str

# isort: split
# TODO: all request handlers should be safely imported
from . import _urllib  # noqa: F401


class RequestDirector:
    """RequestDirector class

    Helper class that, when given a request, forward it to a RequestHandler that supports it.

    @param logger: Logger instance.
    @param verbose: Print debug request information to stdout.
    """

    def __init__(self, logger, verbose=False):
        self.handlers: dict[str, RequestHandler] = {}
        self.logger = logger  # TODO(Grub4k): default logger
        self.verbose = verbose

    def close(self):
        for handler in self.handlers.values():
            handler.close()

    def add_handler(self, handler: RequestHandler):
        """Add a handler. If a handler of the same RH_KEY exists, it will overwrite it"""
        assert isinstance(handler, RequestHandler), 'handler must be a RequestHandler'
        self.handlers[handler.RH_KEY] = handler

    def _print_verbose(self, msg):
        if self.verbose:
            self.logger.stdout(f'director: {msg}')

    def send(self, request: Request) -> Response:
        """
        Passes a request onto a suitable RequestHandler
        """
        if not self.handlers:
            raise RequestError('No request handlers configured')

        assert isinstance(request, Request)

        unexpected_errors = []
        unsupported_errors = []
        # TODO (future): add a per-request preference system
        for handler in reversed(list(self.handlers.values())):
            self._print_verbose(f'Checking if "{handler.RH_NAME}" supports this request.')
            try:
                handler.validate(request)
            except UnsupportedRequest as e:
                self._print_verbose(
                    f'"{handler.RH_NAME}" cannot handle this request (reason: {error_to_str(e)})')
                unsupported_errors.append(e)
                continue

            self._print_verbose(f'Sending request via "{handler.RH_NAME}"')
            try:
                response = handler.send(request)
            except RequestError:
                raise
            except Exception as e:
                self.logger.error(
                    f'[{handler.RH_NAME}] Unexpected error: {error_to_str(e)}{bug_reports_message()}',
                    is_error=False)
                unexpected_errors.append(e)
                continue

            assert isinstance(response, Response)
            return response

        raise NoSupportingHandlers(unsupported_errors, unexpected_errors)
