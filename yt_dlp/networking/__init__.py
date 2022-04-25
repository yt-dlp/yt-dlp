from ._urllib import UrllibRH
from .common import UnsupportedRH

try:
    from ._urllib3 import Urllib3RH
    has_urllib3 = True
except ImportError:
    has_urllib3 = False
    Urllib3RH = None

REQUEST_HANDLERS = [UnsupportedRH, UrllibRH]
if Urllib3RH is not None:
    REQUEST_HANDLERS.append(Urllib3RH)

__all__ = ['UrllibRH', 'UnsupportedRH', 'Urllib3RH', 'REQUEST_HANDLERS', 'has_urllib3']
