# flake8: noqa: F401
import warnings

from .common import (
    HEADRequest,
    PATCHRequest,
    PUTRequest,
    Request,
    RequestDirector,
    RequestHandler,
    Response,
)

# isort: split
# TODO: all request handlers should be safely imported
from . import _urllib
from ..utils import bug_reports_message

try:
    from . import _requests
except ImportError:
    pass
except Exception as e:
    warnings.warn(f'Failed to import "_requests" request handler: {e}' + bug_reports_message())

try:
    from . import _websockets
except ImportError:
    pass
except Exception as e:
    warnings.warn(f'Failed to import "_websockets" request handler: {e}' + bug_reports_message())

try:
    from . import _curlcffi
except ImportError:
    pass
except Exception as e:
    warnings.warn(f'Failed to import "_curlcffi" request handler: {e}' + bug_reports_message())
