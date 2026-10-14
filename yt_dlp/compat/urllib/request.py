from urllib.request import *  # noqa: F403

from ..compat_utils import passthrough_module

passthrough_module(__name__, 'urllib.request')
del passthrough_module
