"""Deprecated - New code should avoid these"""
import warnings

from .compat_utils import passthrough_module

# XXX: Implement this the same way as other DeprecationWarnings without circular import
passthrough_module(__name__, '.._legacy', callback=lambda attr: warnings.warn(
    DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=6))
del passthrough_module

import functools  # noqa: F401
import os


compat_os_name = os.name
compat_realpath = os.path.realpath


def compat_shlex_quote(s):
    from ..utils import shell_quote
    return shell_quote(s)
