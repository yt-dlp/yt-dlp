from __future__ import annotations

from .common import Request, RequestHandler, Response
from .exceptions import NoSupportingHandlers, RequestError, UnsupportedRequest
from ..utils import bug_reports_message, error_to_str

_PREFERENCES = []


def register_preference(preference: type[Preference]):
    """Register a RequestHandler class"""
    assert issubclass(preference, Preference), f'{preference} must be a subclass of Preference'
    assert preference not in _PREFERENCES, f'{preference} is already registered'
    _PREFERENCES.append(preference)
    return preference


class Preference:
    """Preference class

    Used by RequestDirector to determine the order in which RequestHandlers should be tried for a given request.
    The higher the preference, the higher the priority of the handler.

    _RH_KEY: optional, to restrict the preference to a specific RequestHandler
    _PREFERENCE: optional, to add a fixed relative preference for a handler. Takes precedence over _get_preference.

    If subclasses do not set _PREFERENCE, they should implement _get_preference
     to dynamically generate a preference based off the request and handler.

    The returned preference should be an integer. The default preference is 0.
    """
    _RH_KEY: str = None
    _PREFERENCE: int = None

    def get_preference(self, request: Request, handler: RequestHandler) -> int:
        if self._RH_KEY is not None and handler.RH_KEY != self._RH_KEY:
            return 0
        elif self._PREFERENCE is not None:
            return self._PREFERENCE
        return self._get_preference(request, handler)

    def _get_preference(self, request: Request, handler: RequestHandler) -> int:
        """Generate a preference for the given request and handler. Implement this method in subclasses"""
        return 0


class RequestDirector:
    """RequestDirector class

    Helper class that, when given a request, forward it to a RequestHandler that supports it.

    @param logger: Logger instance.
    @param verbose: Print debug request information to stdout.
    """

    def __init__(self, logger, verbose=False):
        self.handlers: dict[str, RequestHandler] = {}
        self.preferences: set[Preference] = set()
        self.logger = logger  # TODO(Grub4k): default logger
        self.verbose = verbose

    def close(self):
        for handler in self.handlers.values():
            handler.close()

    def add_handler(self, handler: RequestHandler):
        """Add a handler. If a handler of the same RH_KEY exists, it will overwrite it"""
        assert isinstance(handler, RequestHandler), 'handler must be a RequestHandler'
        self.handlers[handler.RH_KEY] = handler

    def add_preference(self, preference: "Preference"):
        assert isinstance(preference, Preference), 'preference must be a Preference'
        self.preferences.add(preference)

    def _print_verbose(self, msg):
        if self.verbose:
            self.logger.stdout(f'director: {msg}')

    def _sort_handlers(self, request: Request) -> list[RequestHandler]:
        """
        Sorts handlers by preference, given a request
        """
        handler_preferences = {}
        for rh_key, handler in self.handlers.items():
            handler_preferences.setdefault(rh_key, 0)
            for preference in self.preferences:
                handler_preferences[rh_key] += preference.get_preference(request, handler)
        self._print_verbose(f'Handler preferences for this request: {handler_preferences}')
        return sorted(self.handlers.values(), key=lambda h: handler_preferences[h.RH_KEY], reverse=True)

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
        for handler in self._sort_handlers(request):
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
