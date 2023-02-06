import collections
import contextlib
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


class EnhancedModule(types.ModuleType):
    def __new__(cls, name, *args, **kwargs):
        if name not in sys.modules:
            return super().__new__(cls, name, *args, **kwargs)

        assert not args and not kwargs, 'Cannot pass additional arguments to an existing module'
        module = sys.modules[name]
        module.__class__ = cls
        return module

    def __init__(self, name, *args, **kwargs):
        # Prevent __new__ from trigerring __init__ again
        if name not in sys.modules:
            super().__init__(name, *args, **kwargs)

    def __bool__(self):
        return vars(self).get('__bool__', lambda: True)()

    def __getattribute__(self, attr):
        try:
            ret = super().__getattribute__(attr)
        except AttributeError:
            if attr.startswith('__') and attr.endswith('__'):
                raise
            getter = getattr(self, '__getattr__', None)
            if not getter:
                raise
            ret = getter(attr)
        return ret.fget() if isinstance(ret, property) else ret


def passthrough_module(parent, child, allowed_attributes=None, *, callback=lambda _: None):
    """Passthrough parent module into a child module, creating the parent if necessary"""
    parent = EnhancedModule(parent)

    def __getattr__(attr):
        if _is_package(parent):
            with contextlib.suppress(ImportError):
                return importlib.import_module(f'.{attr}', parent.__name__)

        ret = from_child(attr)
        if ret is _NO_ATTRIBUTE:
            raise AttributeError(f'module {parent.__name__} has no attribute {attr}')
        callback(attr)
        return ret

    def from_child(attr):
        nonlocal child

        if allowed_attributes is None:
            if attr.startswith('__') and attr.endswith('__'):
                return _NO_ATTRIBUTE
        elif attr not in allowed_attributes:
            return _NO_ATTRIBUTE

        if isinstance(child, str):
            child = importlib.import_module(child, parent.__name__)

        with contextlib.suppress(AttributeError):
            return getattr(child, attr)

        if _is_package(child):
            with contextlib.suppress(ImportError):
                return importlib.import_module(f'.{attr}', child.__name__)

        return _NO_ATTRIBUTE

    parent.__getattr__ = __getattr__
    return parent
