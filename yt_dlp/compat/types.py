# flake8: noqa: F405
from types import *  # noqa: F403

from .compat_utils import passthrough_module

passthrough_module(__name__, 'types')
del passthrough_module

try:
    NoneType  # >= 3.10
except NameError:
    NoneType = type(None)
