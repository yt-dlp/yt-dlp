from ..compat.compat_utils import passthrough_module

try:
    import Cryptodome as _parent
except ImportError:
    try:
        import Crypto as _parent
    except (ImportError, SyntaxError):  # Old Crypto gives SyntaxError in newer Python
        _parent = passthrough_module(__name__, 'no_Cryptodome')
        __bool__ = lambda: False

del passthrough_module

__version__ = ''
AES = PKCS1_v1_5 = Blowfish = PKCS1_OAEP = SHA1 = CMAC = RSA = None
try:
    if _parent.__name__ == 'Cryptodome':
        from Cryptodome import __version__
        from Cryptodome.Cipher import AES, PKCS1_OAEP, Blowfish, PKCS1_v1_5
        from Cryptodome.Hash import CMAC, SHA1
        from Cryptodome.PublicKey import RSA
    elif _parent.__name__ == 'Crypto':
        from Crypto import __version__
        from Crypto.Cipher import AES, PKCS1_OAEP, Blowfish, PKCS1_v1_5  # noqa: F401
        from Crypto.Hash import CMAC, SHA1  # noqa: F401
        from Crypto.PublicKey import RSA  # noqa: F401
except ImportError:
    __version__ = f'broken {__version__}'.strip()


_yt_dlp__identifier = _parent.__name__
if AES and _yt_dlp__identifier == 'Crypto':
    try:
        # In pycrypto, mode defaults to ECB. See:
        # https://www.pycryptodome.org/en/latest/src/vs_pycrypto.html#:~:text=not%20have%20ECB%20as%20default%20mode
        AES.new(b'abcdefghijklmnop')
    except TypeError:
        _yt_dlp__identifier = 'pycrypto'
