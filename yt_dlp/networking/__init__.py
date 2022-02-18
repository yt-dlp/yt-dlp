from ._urllib import UrllibHandler
from .common import UnsupportedBackendHandler

network_handlers = [UnsupportedBackendHandler, UrllibHandler]

__all__ = ['UrllibHandler', 'UnsupportedBackendHandler', 'network_handlers']
