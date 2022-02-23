from ._urllib import UrllibBackendAdapter
from .common import UnsupportedBackend

try:
    from ._urllib3 import Urllib3Handler
    has_urllib3 = True
except ImportError:
    has_urllib3 = False
    Urllib3Handler = None
network_handlers = [UnsupportedBackend, UrllibBackendAdapter, Urllib3Handler]
__all__ = ['UrllibBackendAdapter', 'UnsupportedBackend', 'network_handlers', 'has_urllib3']
