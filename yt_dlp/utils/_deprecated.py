"""Deprecated - New code should avoid these"""
import warnings

from ..compat.compat_utils import passthrough_module

# XXX: Implement this the same way as other DeprecationWarnings without circular import
passthrough_module(__name__, '.._legacy', callback=lambda attr: warnings.warn(
    DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=6))
del passthrough_module


from ._utils import preferredencoding


def encodeFilename(s, for_subprocess=False):
    assert isinstance(s, str)
    return s


def decodeFilename(b, for_subprocess=False):
    return b


def decodeArgument(b):
    return b


def decodeOption(optval):
    if optval is None:
        return optval
    if isinstance(optval, bytes):
        optval = optval.decode(preferredencoding())

    assert isinstance(optval, str)
    return optval


def error_to_compat_str(err):
    return str(err)
