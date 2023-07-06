# flake8: noqa: F401, F403
import warnings

from ..compat.compat_utils import passthrough_module

# XXX: Implement this the same way as other DeprecationWarnings without circular import
passthrough_module(__name__, '._legacy', callback=lambda attr: warnings.warn(
    DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=5))
del passthrough_module

# isort: off
from .traversal import *
from ._utils import *
from ._utils import _configuration_args, _get_exe_version_output
from ._deprecated import *
