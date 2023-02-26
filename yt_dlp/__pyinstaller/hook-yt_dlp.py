import ast
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


def find_attribute_accesses(node, name, path=()):
    if isinstance(node, ast.Attribute):
        path = [*path, node.attr]
        if isinstance(node.value, ast.Name) and node.value.id == name:
            yield path[::-1]
    for child in ast.iter_child_nodes(node):
        yield from find_attribute_accesses(child, name, path)


def collect_used_submodules(name, level):
    for dirpath, _, filenames in os.walk(Path(__file__).parent.parent):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            with open(Path(dirpath) / filename, encoding='utf8') as f:
                for submodule in find_attribute_accesses(ast.parse(f.read()), name):
                    yield '.'.join(submodule[:level])


def pycryptodome_module():
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


def get_hidden_imports():
    yield 'yt_dlp.compat._legacy'
    yield from collect_submodules('websockets')

    crypto = pycryptodome_module()
    for sm in set(collect_used_submodules('Cryptodome', 2)):
        yield f'{crypto}.{sm}'

    # These are auto-detected, but explicitly add them just in case
    yield from ('mutagen', 'brotli', 'certifi')


hiddenimports = list(get_hidden_imports())
print(f'Adding imports: {hiddenimports}')

excludedimports = ['youtube_dl', 'youtube_dlc', 'test', 'ytdlp_plugins', 'devscripts']
