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


def passthrough_module(parent, child, allowed_attributes=None, *, callback=lambda _: None):
    parent_module = importlib.import_module(parent)
    child_module = None  # Import child module only as needed

    class PassthroughModule(types.ModuleType):
        def __getattr__(self, attr):
            if _is_package(parent_module):
                with contextlib.suppress(ImportError):
                    return importlib.import_module(f'.{attr}', parent)

            ret = self.__from_child(attr)
            if ret is _NO_ATTRIBUTE:
                raise AttributeError(f'module {parent} has no attribute {attr}')
            callback(attr)
            return ret

        def __from_child(self, attr):
            if allowed_attributes is None:
                if attr.startswith('__') and attr.endswith('__'):
                    return _NO_ATTRIBUTE
            elif attr not in allowed_attributes:
                return _NO_ATTRIBUTE

            nonlocal child_module
            child_module = child_module or importlib.import_module(child, parent)

            with contextlib.suppress(AttributeError):
                return getattr(child_module, attr)

            if _is_package(child_module):
                with contextlib.suppress(ImportError):
                    return importlib.import_module(f'.{attr}', child)

            return _NO_ATTRIBUTE

    # Python 3.6 does not have module level __getattr__
    # https://peps.python.org/pep-0562/
    sys.modules[parent].__class__ = PassthroughModule
