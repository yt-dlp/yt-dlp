# flake8: noqa: F403
from ..compat.compat_utils import passthrough_module

passthrough_module(__name__, '._deprecated')
del passthrough_module

# isort: off
from .traversal import *
from ._utils import *
from ._utils import _configuration_args, _get_exe_version_output  # noqa: F401
