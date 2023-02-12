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


from . import Cryptodome

all_dependencies = {k: v for k, v in globals().items() if not k.startswith('_')}
available_dependencies = {k: v for k, v in all_dependencies.items() if v}


# Deprecated
Cryptodome_AES = Cryptodome.Cipher.AES if Cryptodome else None


__all__ = [
    'all_dependencies',
    'available_dependencies',
    *all_dependencies.keys(),
]
