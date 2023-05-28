"""Deprecated - New code should avoid these"""

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
