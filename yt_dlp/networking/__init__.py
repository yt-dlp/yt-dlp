# flake8: noqa: F401
import warnings

from .common import (
    HEADRequest,
    PUTRequest,
    Request,
    RequestDirector,
    RequestHandler,
    Response,
)

# isort: split
# TODO: all request handlers should be safely imported
from . import _urllib

try:
    from . import _curlcffi  # noqa: F401
except ImportError:
    pass
except Exception as e:
    warnings.warn(f'Failed to import curl_cffi handler: {e}')
