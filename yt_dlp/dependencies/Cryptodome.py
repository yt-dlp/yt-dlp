import types

from ..compat import functools
from ..compat.compat_utils import passthrough_module

try:
    import Cryptodome as _parent
except ImportError:
    try:
        import Crypto as _parent
    except (ImportError, SyntaxError):  # Old Crypto gives SyntaxError in newer Python
        _parent = types.ModuleType('no_Cryptodome')
        __bool__ = lambda: False

passthrough_module(__name__, _parent, (..., '__version__'))
del passthrough_module


@property
@functools.cache
def _yt_dlp__identifier():
    if _parent.__name__ == 'Crypto':
        from Crypto.Cipher import AES
        try:
            # In pycrypto, mode defaults to ECB. See:
            # https://www.pycryptodome.org/en/latest/src/vs_pycrypto.html#:~:text=not%20have%20ECB%20as%20default%20mode
            AES.new(b'abcdefghijklmnop')
        except TypeError:
            return 'pycrypto'
    return _parent.__name__
