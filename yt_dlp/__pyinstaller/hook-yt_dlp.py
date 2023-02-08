import sys

from PyInstaller.utils.hooks import collect_submodules


def _pycryptodome_module():
    try:
        import Cryptodome  # noqa: F401
    except ImportError:
        try:
            import Crypto  # noqa: F401
            print('WARNING: Using Crypto since Cryptodome is not available. '
                  'Install with: pip install pycryptodomex', file=sys.stderr)
            return 'Crypto'
        except ImportError:
            pass
    return 'Cryptodome'


def _hidden_imports():
    yield 'yt_dlp.compat._legacy'
    for m in [_pycryptodome_module(), 'websockets']:
        yield from collect_submodules(m)
    # These are auto-detected, but explicitly add them just in case
    yield from ('mutagen', 'brotli', 'certifi')


hiddenimports = list(_hidden_imports())
excludedimports = ['youtube_dl', 'youtube_dlc', 'test', 'ytdlp_plugins', 'devscripts']
