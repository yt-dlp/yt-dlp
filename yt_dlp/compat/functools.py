# flake8: noqa: F405
from functools import *  # noqa: F403

from .compat_utils import passthrough_module

passthrough_module(__name__, 'functools')
del passthrough_module

try:
    cache  # >= 3.9
except NameError:
    cache = lru_cache(maxsize=None)

try:
    cached_property  # >= 3.8
except NameError:
    class cached_property:
        def __init__(self, func):
            update_wrapper(self, func)
            self.func = func

        def __get__(self, instance, _):
            if instance is None:
                return self
            setattr(instance, self.func.__name__, self.func(instance))
            return getattr(instance, self.func.__name__)
