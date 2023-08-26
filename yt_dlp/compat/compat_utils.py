import collections
import contextlib
import functools
import importlib
import sys
import types

_NO_ATTRIBUTE = object()

_Package = collections.namedtuple('Package', ('name', 'version'))


def get_package_info(module):
    return _Package(
        name=getattr(module, '_yt_dlp__identifier', module.__name__),
        version=str(next(filter(None, (
            getattr(module, attr, None)
            for attr in ('__version__', 'version_string', 'version')
        )), None)))


def _is_package(module):
    return '__path__' in vars(module)


def _is_dunder(name):
    return name.startswith('__') and name.endswith('__')


class EnhancedModule(types.ModuleType):
    def __bool__(self):
        return vars(self).get('__bool__', lambda: True)()

    def __getattribute__(self, attr):
        try:
            ret = super().__getattribute__(attr)
        except AttributeError:
            if _is_dunder(attr):
                raise
            getter = getattr(self, '__getattr__', None)
            if not getter:
                raise
            ret = getter(attr)
        return ret.fget() if isinstance(ret, property) else ret


def passthrough_module(parent, child, allowed_attributes=(..., ), *, callback=lambda _: None):
    """Passthrough parent module into a child module, creating the parent if necessary"""
    def __getattr__(attr):
        if _is_package(parent):
            with contextlib.suppress(ModuleNotFoundError):
                return importlib.import_module(f'.{attr}', parent.__name__)

        ret = from_child(attr)
        if ret is _NO_ATTRIBUTE:
            raise AttributeError(f'module {parent.__name__} has no attribute {attr}')
        callback(attr)
        return ret

    @functools.lru_cache(maxsize=None)
    def from_child(attr):
        nonlocal child
        if attr not in allowed_attributes:
            if ... not in allowed_attributes or _is_dunder(attr):
                return _NO_ATTRIBUTE

        if isinstance(child, str):
            child = importlib.import_module(child, parent.__name__)

        if _is_package(child):
            with contextlib.suppress(ImportError):
                return passthrough_module(f'{parent.__name__}.{attr}',
                                          importlib.import_module(f'.{attr}', child.__name__))

        with contextlib.suppress(AttributeError):
            return getattr(child, attr)

        return _NO_ATTRIBUTE

    parent = sys.modules.get(parent, types.ModuleType(parent))
    parent.__class__ = EnhancedModule
    parent.__getattr__ = __getattr__
    return parent
