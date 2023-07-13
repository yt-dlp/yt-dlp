from .common import Request, RequestHandler, Response
from .exceptions import NoSupportingHandlers, RequestError, UnsupportedRequest

# isort: split
# TODO: all request handlers should be safely imported
from . import _urllib  # noqa: F401
try:
    from . import _curlcffi
except ImportError:
    pass

from .director import RequestDirector  # noqa: F401

