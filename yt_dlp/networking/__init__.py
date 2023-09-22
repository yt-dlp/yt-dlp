# flake8: noqa: 401
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
from ..utils import bug_reports_message

try:
    from . import _requests
except ImportError:
    pass
except Exception as e:
    warnings.warn(f'Unable to import requests handler: {e}' + bug_reports_message())
