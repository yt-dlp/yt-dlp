# flake8: noqa: F405
from functools import *  # noqa: F403

from .compat_utils import passthrough_module

passthrough_module(__name__, 'functools')
del passthrough_module

try:
    cache  # >= 3.9
except NameError:
    cache = lru_cache(maxsize=None)
