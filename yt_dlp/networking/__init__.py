from ._urllib import UrllibBackendAdapter
from .common import UnsupportedBackend

network_handlers = [UnsupportedBackend, UrllibBackendAdapter]

__all__ = ['UrllibBackendAdapter', 'UnsupportedBackend', 'network_handlers']
