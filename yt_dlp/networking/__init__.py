from ._urllib import UrllibHandler
from .common import UnsupportedBackendHandler

try:
    from ._urllib3 import Urllib3Handler
    has_urllib3 = True
except ImportError:
    has_urllib3 = False
    Urllib3Handler = None

network_handlers = [UnsupportedBackendHandler, UrllibHandler, Urllib3Handler]

__all__ = ['UrllibHandler', 'UnsupportedBackendHandler', 'network_handlers', 'has_urllib3']
