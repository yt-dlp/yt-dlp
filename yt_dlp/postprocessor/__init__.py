from ..compat.compat_utils import passthrough_module
from ..globals import ALL_PPS

passthrough_module(__name__, '.postprocessors', (..., '__all__'))
del passthrough_module


def get_postprocessor(key):
    from . import postprocessors  # noqa: F401
    return ALL_PPS.get()[f'{key}PP']
