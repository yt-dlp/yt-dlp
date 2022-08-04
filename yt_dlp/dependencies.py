# flake8: noqa: F401
"""Imports all optional dependencies for the project.
An attribute "_yt_dlp__identifier" may be inserted into the module if it uses an ambiguous namespace"""

try:
    import brotlicffi as brotli
except ImportError:
    try:
        import brotli
    except ImportError:
        brotli = None


try:
    import certifi
except ImportError:
    certifi = None
else:
    from os.path import exists as _path_exists

    # The certificate may not be bundled in executable
    if not _path_exists(certifi.where()):
        certifi = None


try:
    from Cryptodome.Cipher import AES as Cryptodome_AES
except ImportError:
    try:
        from Crypto.Cipher import AES as Cryptodome_AES
    except (ImportError, SyntaxError):  # Old Crypto gives SyntaxError in newer Python
        Cryptodome_AES = None
    else:
        try:
            # In pycrypto, mode defaults to ECB. See:
            # https://www.pycryptodome.org/en/latest/src/vs_pycrypto.html#:~:text=not%20have%20ECB%20as%20default%20mode
            Cryptodome_AES.new(b'abcdefghijklmnop')
        except TypeError:
            pass
        else:
            Cryptodome_AES._yt_dlp__identifier = 'pycrypto'


try:
    import mutagen
except ImportError:
    mutagen = None


secretstorage = None
try:
    import secretstorage
    _SECRETSTORAGE_UNAVAILABLE_REASON = None
except ImportError:
    _SECRETSTORAGE_UNAVAILABLE_REASON = (
        'as the `secretstorage` module is not installed. '
        'Please install by running `python3 -m pip install secretstorage`')
except Exception as _err:
    _SECRETSTORAGE_UNAVAILABLE_REASON = f'as the `secretstorage` module could not be initialized. {_err}'


try:
    import sqlite3
except ImportError:
    # although sqlite3 is part of the standard library, it is possible to compile python without
    # sqlite support. See: https://github.com/yt-dlp/yt-dlp/issues/544
    sqlite3 = None


try:
    import websockets
except (ImportError, SyntaxError):
    # websockets 3.10 on python 3.6 causes SyntaxError
    # See https://github.com/yt-dlp/yt-dlp/issues/2633
    websockets = None


try:
    import xattr  # xattr or pyxattr
except ImportError:
    xattr = None
else:
    if hasattr(xattr, 'set'):  # pyxattr
        xattr._yt_dlp__identifier = 'pyxattr'


all_dependencies = {k: v for k, v in globals().items() if not k.startswith('_')}


available_dependencies = {k: v for k, v in all_dependencies.items() if v}


__all__ = [
    'all_dependencies',
    'available_dependencies',
    *all_dependencies.keys(),
]
