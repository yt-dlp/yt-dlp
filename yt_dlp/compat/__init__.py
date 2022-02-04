import contextlib
import os
import subprocess
import sys
import types
import xml.etree.ElementTree as etree

from . import re
from ._deprecated import *  # noqa: F401, F403


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


try:
    import websockets as compat_websockets
except ImportError:
    compat_websockets = None

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


try:
    from Cryptodome.Cipher import AES as compat_pycrypto_AES
except ImportError:
    try:
        from Crypto.Cipher import AES as compat_pycrypto_AES
    except ImportError:
        compat_pycrypto_AES = None

try:
    import brotlicffi as compat_brotli
except ImportError:
    try:
        import brotli as compat_brotli
    except ImportError:
        compat_brotli = None

WINDOWS_VT_MODE = False if compat_os_name == 'nt' else None


def windows_enable_vt_mode():  # TODO: Do this the proper way https://bugs.python.org/issue30075
    if compat_os_name != 'nt':
        return
    global WINDOWS_VT_MODE
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    with contextlib.suppress(Exception):
        subprocess.Popen('', shell=True, startupinfo=startupinfo).wait()
        WINDOWS_VT_MODE = True


class _PassthroughLegacy(types.ModuleType):
    def __getattr__(self, attr):
        import importlib
        with contextlib.suppress(ImportError):
            return importlib.import_module(f'.{attr}', __name__)

        legacy = importlib.import_module('._legacy', __name__)
        if not hasattr(legacy, attr):
            raise AttributeError(f'module {__name__} has no attribute {attr}')

        # XXX: Implement this the same way as other DeprecationWarnings without circular import
        import warnings
        warnings.warn(DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=2)
        return getattr(legacy, attr)


# Python 3.6 does not have module level __getattr__
# https://peps.python.org/pep-0562/
sys.modules[__name__].__class__ = _PassthroughLegacy
