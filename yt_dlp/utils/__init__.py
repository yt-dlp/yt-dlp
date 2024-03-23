# flake8: noqa: F403
from ..compat.compat_utils import passthrough_module

passthrough_module(__name__, '._deprecated')
del passthrough_module

# isort: off
from .traversal import *
from ._utils import *
from ._utils import _configuration_args, _get_exe_version_output  # noqa: F401

def txt_or_none(v, default=None):
    """ Combine str/strip_or_none, disallow blank value (for traverse_obj) """
    return default if v is None else (str(v).strip() or default)

def T(x):
    """ For use in yt-dl instead of {type} or set((type,)) """
    return set((x,))
