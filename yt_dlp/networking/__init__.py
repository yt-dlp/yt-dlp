from .common import Request  # noqa: F401

# isort: split
# TODO: all request handlers should be safely imported
from . import _urllib  # noqa: F401
try:
    from . import _curlcffi  # noqa: F401
except ImportError:
    pass

from .director import RequestDirector  # noqa: F401
