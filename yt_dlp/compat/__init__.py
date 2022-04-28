import os
import sys
import warnings
import xml.etree.ElementTree as etree

from . import re
from ._deprecated import *  # noqa: F401, F403
from .compat_utils import passthrough_module


# XXX: Implement this the same way as other DeprecationWarnings without circular import
passthrough_module(__name__, '._legacy', callback=lambda attr: warnings.warn(
    DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=2))
del passthrough_module


# HTMLParseError has been deprecated in Python 3.3 and removed in
# Python 3.5. Introducing dummy exception for Python >3.5 for compatible
# and uniform cross-version exception handling
class compat_HTMLParseError(Exception):
    pass


class _TreeBuilder(etree.TreeBuilder):
    def doctype(self, name, pubid, system):
        pass


def compat_etree_fromstring(text):
    return etree.XML(text, parser=etree.XMLParser(target=_TreeBuilder()))


compat_os_name = os._name if os.name == 'java' else os.name


if compat_os_name == 'nt':
    import ctypes

    def compat_shlex_quote(s):
        return s if re.match(r'^[-_\w./]+$', s) else '"%s"' % s.replace('"', '\\"')
else:
    from shlex import quote as compat_shlex_quote  # noqa: F401


def compat_ord(c):
    return c if isinstance(c, int) else ord(c)


def compat_setenv(key, value, env=os.environ):
    env[key] = value


if compat_os_name == 'nt' and sys.version_info < (3, 8):
    # os.path.realpath on Windows does not follow symbolic links
    # prior to Python 3.8 (see https://bugs.python.org/issue9949)
    def compat_realpath(path):
        while os.path.islink(path):
            path = os.path.abspath(os.readlink(path))
        return path
else:
    compat_realpath = os.path.realpath


# Python 3.8+ does not honor %HOME% on windows, but this breaks compatibility with youtube-dl
# See https://github.com/yt-dlp/yt-dlp/issues/792
# https://docs.python.org/3/library/os.path.html#os.path.expanduser
if compat_os_name in ('nt', 'ce'):
    def compat_expanduser(path):
        HOME = os.environ.get('HOME')
        if not HOME:
            return os.path.expanduser(path)
        elif not path.startswith('~'):
            return path
        i = path.replace('\\', '/', 1).find('/')  # ~user
        if i < 0:
            i = len(path)
        userhome = os.path.join(os.path.dirname(HOME), path[1:i]) if i > 1 else HOME
        return userhome + path[i:]
else:
    compat_expanduser = os.path.expanduser


WINDOWS_VT_MODE = False if compat_os_name == 'nt' else None


def set_windows_conout_mode(new_mode, mask=0xffffffff):
    # based on https://github.com/python/cpython/issues/74261#issuecomment-1093745755
    from ctypes import wintypes

    INVALID_HANDLE_VALUE = 0xffffffff  # ((DWORD)-1)
    STD_OUTPUT_HANDLE = 0xfffffff5  # ((DWORD)-11)

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    def check_bool(result, func, args):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return args

    def check_handle(result, func, args):
        if not result or result == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error(), 'Couldn\'t find handle')
        return args

    kernel32.GetStdHandle.errcheck = check_handle
    kernel32.GetStdHandle.argtypes = (wintypes.DWORD,)
    kernel32.GetConsoleMode.errcheck = check_bool
    kernel32.GetConsoleMode.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.SetConsoleMode.errcheck = check_bool
    kernel32.SetConsoleMode.argtypes = (wintypes.HANDLE, wintypes.DWORD)

    hout = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    out = wintypes.DWORD()
    kernel32.GetConsoleMode(hout, ctypes.byref(out))
    old_mode = out.value
    mode = (new_mode & mask) | (old_mode & ~mask)
    kernel32.SetConsoleMode(hout, mode)
    return old_mode


def windows_enable_vt_mode():
    if compat_os_name != 'nt':
        return
    global WINDOWS_VT_MODE
    ERROR_INVALID_PARAMETER = 0x0057
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    DISABLE_NEWLINE_AUTO_RETURN = 0x0008

    mode = mask = ENABLE_VIRTUAL_TERMINAL_PROCESSING | DISABLE_NEWLINE_AUTO_RETURN
    try:
        mode = set_windows_conout_mode(mode, mask)
        WINDOWS_VT_MODE = True
        return mode
    except OSError as e:
        if e.winerror != ERROR_INVALID_PARAMETER:  # any other error than not supported os
            raise e
