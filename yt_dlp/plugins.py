import contextlib
import enum
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import inspect
import itertools
import os
import pkgutil
import sys
import traceback
import zipimport
from pathlib import Path
from zipfile import ZipFile

from .globals import (
    extractors,
    plugin_dirs,
    plugin_ies,
    plugin_pps,
    postprocessors,
)

from .compat import functools  # isort: split
from .utils import (
    get_executable_path,
    get_system_config_dirs,
    get_user_config_dirs,
    merge_dicts,
    orderedSet,
    write_string,
)

PACKAGE_NAME = 'yt_dlp_plugins'
COMPAT_PACKAGE_NAME = 'ytdlp_plugins'
_BASE_PACKAGE_PATH = Path(__file__).parent


class PluginType(enum.Enum):
    POSTPROCESSORS = ('postprocessor', 'PP')
    EXTRACTORS = ('extractor', 'IE')


_plugin_type_lookup = {
    PluginType.POSTPROCESSORS: (postprocessors, plugin_pps),
    PluginType.EXTRACTORS: (extractors, plugin_ies),
}


class PluginLoader(importlib.abc.Loader):
    """Dummy loader for virtual namespace packages"""

    def exec_module(self, module):
        return None


@functools.cache
def dirs_in_zip(archive):
    try:
        with ZipFile(archive) as zip_:
            return set(
                itertools.chain.from_iterable(
                    Path(file).parents for file in zip_.namelist()
                ),
            )
    except FileNotFoundError:
        pass
    except Exception as e:
        write_string(f'WARNING: Could not read zip file {archive}: {e}\n')
    return ()


def default_plugin_paths():
    def _get_package_paths(*root_paths, containing_folder):
        for config_dir in orderedSet(map(Path, root_paths), lazy=True):
            # We need to filter the base path added when running __main__.py directly
            if config_dir == _BASE_PACKAGE_PATH:
                continue
            with contextlib.suppress(OSError):
                yield from (config_dir / containing_folder).iterdir()

    # Load from yt-dlp config folders
    yield from _get_package_paths(
        *get_user_config_dirs('yt-dlp'),
        *get_system_config_dirs('yt-dlp'),
        containing_folder='plugins',
    )

    # Load from yt-dlp-plugins folders
    yield from _get_package_paths(
        get_executable_path(),
        *get_user_config_dirs(''),
        *get_system_config_dirs(''),
        containing_folder='yt-dlp-plugins',
    )

    # Load from PYTHONPATH folders
    yield from (path for path in map(Path, sys.path) if path != _BASE_PACKAGE_PATH)
    # yield from _get_package_paths(*sys.path, containing_folder='')


class PluginFinder(importlib.abc.MetaPathFinder):
    """
    This class provides one or multiple namespace packages.
    It searches in sys.path and yt-dlp config folders for
    the existing subdirectories from which the modules can be imported
    """

    def __init__(self, *packages):
        self._zip_content_cache = {}
        self.packages = set(
            itertools.chain.from_iterable(
                itertools.accumulate(name.split('.'), lambda a, b: '.'.join((a, b)))
                for name in packages
            ),
        )

    def search_locations(self, fullname):
        candidate_locations = itertools.chain.from_iterable(
            default_plugin_paths() if candidate is ... else Path(candidate).iterdir()
            for candidate in plugin_dirs.get()
        )

        parts = Path(*fullname.split('.'))
        for path in orderedSet(candidate_locations, lazy=True):
            candidate = path / parts
            try:
                if candidate.is_dir():
                    yield candidate
                elif path.suffix in ('.zip', '.egg', '.whl') and path.is_file():
                    if parts in dirs_in_zip(path):
                        yield candidate
            except PermissionError as e:
                write_string(f'Permission error while accessing modules in "{e.filename}"\n')

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.packages:
            return None

        search_locations = list(map(str, self.search_locations(fullname)))
        if not search_locations:
            return None

        spec = importlib.machinery.ModuleSpec(fullname, PluginLoader(), is_package=True)
        spec.submodule_search_locations = search_locations
        return spec

    def invalidate_caches(self):
        dirs_in_zip.cache_clear()
        for package in self.packages:
            if package in sys.modules:
                del sys.modules[package]


def directories():
    spec = importlib.util.find_spec(PACKAGE_NAME)
    return spec.submodule_search_locations if spec else []


def iter_modules(subpackage):
    fullname = f'{PACKAGE_NAME}.{subpackage}'
    with contextlib.suppress(ModuleNotFoundError):
        pkg = importlib.import_module(fullname)
        yield from pkgutil.iter_modules(path=pkg.__path__, prefix=f'{fullname}.')


def load_module(module, module_name, suffix):
    result =  inspect.getmembers(module, lambda obj: (
        inspect.isclass(obj)
        and obj.__name__.endswith(suffix)
        and obj.__module__.startswith(module_name)
        and not obj.__name__.startswith('_')
        and obj.__name__ in getattr(module, '__all__', [obj.__name__])))
    return result


def load_plugins(plugin_type: PluginType):
    destination, plugin_destination = _plugin_type_lookup[plugin_type]
    name, suffix = plugin_type.value
    classes = {}
    if os.environ.get('YTDLP_NO_PLUGINS'):
        return classes

    for finder, module_name, _ in iter_modules(name):
        if any(x.startswith('_') for x in module_name.split('.')):
            continue
        try:
            if sys.version_info < (3, 10) and isinstance(finder, zipimport.zipimporter):
                # zipimporter.load_module() is deprecated in 3.10 and removed in 3.12
                # The exec_module branch below is the replacement for >= 3.10
                # See: https://docs.python.org/3/library/zipimport.html#zipimport.zipimporter.exec_module
                module = finder.load_module(module_name)
            else:
                spec = finder.find_spec(module_name)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
        except Exception:
            write_string(
                f'Error while importing module {module_name!r}\n{traceback.format_exc(limit=-1)}',
            )
            continue
        classes.update(load_module(module, module_name, suffix))

    # Compat: old plugin system using __init__.py
    # Note: plugins imported this way do not show up in directories()
    # nor are considered part of the yt_dlp_plugins namespace package
    if ... in plugin_dirs.get((...,)):
        with contextlib.suppress(FileNotFoundError):
            spec = importlib.util.spec_from_file_location(
                name,
                Path(get_executable_path(), COMPAT_PACKAGE_NAME, name, '__init__.py'),
            )
            plugins = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = plugins
            spec.loader.exec_module(plugins)
            classes.update(load_module(plugins, spec.name, suffix))

   # regular_plugins = {}
    # __init_subclass__ was removed so we manually add overrides
    # for name, klass in classes.items():
    #     plugin_name = getattr(klass, '_plugin_name', None)
    #     if not plugin_name:
    #         regular_plugins[name] = klass
    #         continue

        # FIXME: Most likely something wrong here
        # This does not work as plugin overrides are not available here. They are not imported in plugin_ies.

        # mro = inspect.getmro(klass)
        # super_class = klass.__wrapped__ = mro[mro.index(klass) + 1]
        # klass.PLUGIN_NAME, klass.ie_key = plugin_name, super_class.ie_key
        # klass.IE_NAME = f'{super_class.IE_NAME}+{plugin_name}'
        # while getattr(super_class, '__wrapped__', None):
        #     super_class = super_class.__wrapped__
        # setattr(sys.modules[super_class.__module__], super_class.__name__, klass)
        # plugin_overrides.get()[super_class].append(klass)

    # Add the classes into the global plugin lookup
    plugin_destination.set(classes)
    # # We want to prepend to the main lookup
    destination.set(merge_dicts(destination.get(), classes))

    return classes


def load_all_plugin_types():
    # for plugin_type in PluginType:
    #     load_plugins(plugin_type)
    load_plugins(PluginType.EXTRACTORS)


sys.meta_path.insert(0, PluginFinder(f'{PACKAGE_NAME}.extractor', f'{PACKAGE_NAME}.postprocessor'))

__all__ = [
    'directories',
    'load_plugins',
    'load_all_plugin_types',
    'PACKAGE_NAME',
    'COMPAT_PACKAGE_NAME',
]
