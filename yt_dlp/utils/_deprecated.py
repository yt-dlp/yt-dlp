"""Deprecated - New code should avoid these"""
import warnings

from ..compat.compat_utils import passthrough_module

# XXX: Implement this the same way as other DeprecationWarnings without circular import
passthrough_module(__name__, '.._legacy', callback=lambda attr: warnings.warn(
    DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=6))
del passthrough_module


from ._utils import preferredencoding
from ..networking._urllib import HTTPHandler

# isort: split
from .networking import random_user_agent, std_headers  # noqa: F401
from ..networking._urllib import PUTRequest  # noqa: F401
from ..networking._urllib import SUPPORTED_ENCODINGS, HEADRequest  # noqa: F401
from ..networking._urllib import ProxyHandler as PerRequestProxyHandler  # noqa: F401
from ..networking._urllib import RedirectHandler as YoutubeDLRedirectHandler  # noqa: F401
from ..networking._urllib import make_socks_conn_class, update_Request  # noqa: F401
from ..networking.exceptions import network_exceptions  # noqa: F401


def encodeFilename(s, for_subprocess=False):
    assert isinstance(s, str)
    return s


def decodeFilename(b, for_subprocess=False):
    return b


def decodeArgument(b):
    return b


def decodeOption(optval):
    if optval is None:
        return optval
    if isinstance(optval, bytes):
        optval = optval.decode(preferredencoding())

    assert isinstance(optval, str)
    return optval


def error_to_compat_str(err):
    return str(err)


class YoutubeDLHandler(HTTPHandler):
    def __init__(self, params, *args, **kwargs):
        self._params = params
        super().__init__(*args, **kwargs)


YoutubeDLHTTPSHandler = YoutubeDLHandler
