from ._urllib import UrllibBackendAdapter
from .common import UnsupportedBackend

try:
    from ._urllib3 import Urllib3BackendAdapter
    has_urllib3 = True
except ImportError:
    has_urllib3 = False
    Urllib3BackendAdapter = None

network_handlers = [UnsupportedBackend, UrllibBackendAdapter, Urllib3BackendAdapter]
__all__ = ['UrllibBackendAdapter', 'UnsupportedBackend', 'network_handlers', 'has_urllib3']
