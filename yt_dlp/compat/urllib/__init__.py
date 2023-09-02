# flake8: noqa: F405
from urllib import *  # noqa: F403

del request
from . import request  # noqa: F401

from ..compat_utils import passthrough_module

passthrough_module(__name__, 'urllib')
del passthrough_module
