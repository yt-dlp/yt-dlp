import collections
import contextlib
import importlib
import sys
import types


_NO_ATTRIBUTE = object()

_Package = collections.namedtuple('Package', ('name', 'version'))


def get_package_info(module):
    parent = module.__name__.split('.')[0]
    parent_module = None
    with contextlib.suppress(ImportError):
        parent_module = importlib.import_module(parent)

    for attr in ('__version__', 'version_string', 'version'):
        version = getattr(parent_module, attr, None)
        if version is not None:
            break
    return _Package(getattr(module, '_yt_dlp__identifier', parent), str(version))


def _is_package(module):
    try:
        module.__getattribute__('__path__')
    except AttributeError:
        return False
    return True


def passthrough_module(parent, child, *, callback=lambda _: None):
    parent_module = importlib.import_module(parent)
    child_module = importlib.import_module(child, parent)

    class PassthroughModule(types.ModuleType):
        def __getattr__(self, attr):
            if _is_package(parent_module):
                with contextlib.suppress(ImportError):
                    return importlib.import_module(f'.{attr}', parent)

            ret = _NO_ATTRIBUTE
            with contextlib.suppress(AttributeError):
                ret = getattr(child_module, attr)

            if _is_package(child_module):
                with contextlib.suppress(ImportError):
                    ret = importlib.import_module(f'.{attr}', child)

            if ret is _NO_ATTRIBUTE:
                raise AttributeError(f'module {parent} has no attribute {attr}')

            callback(attr)
            return ret

    # Python 3.6 does not have module level __getattr__
    # https://peps.python.org/pep-0562/
    sys.modules[parent].__class__ = PassthroughModule
