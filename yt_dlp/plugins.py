import contextlib
import enum
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import inspect
import itertools
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
    plugin_overrides,
    plugin_pps,
    postprocessors,
)

from .compat import functools  # isort: split
from .utils import (
    get_executable_path,
    get_system_config_dirs,
    get_user_config_dirs,
    merge_dicts,
    write_string,
)

PACKAGE_NAME = 'yt_dlp_plugins'
COMPAT_PACKAGE_NAME = 'ytdlp_plugins'


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
    with contextlib.suppress(FileNotFoundError):
        with ZipFile(archive) as zip:
            return set(itertools.chain.from_iterable(
                Path(file).parents for file in zip.namelist()))
    return ()


def default_plugin_paths():
    seen = set()

    def _get_unique_package_paths(*root_paths, containing_folder):
        for config_dir in map(Path, root_paths):
            plugin_dir = config_dir / containing_folder
            # if plugin_dir in seen:
            #     continue
            seen.add(plugin_dir)
            if not plugin_dir.is_dir():
                continue
            yield from plugin_dir.iterdir()

    # Load from yt-dlp config folders
    yield from _get_unique_package_paths(
        *get_user_config_dirs('yt-dlp'),
        *get_system_config_dirs('yt-dlp'),
        containing_folder='plugins')

    # Load from yt-dlp-plugins folders
    yield from _get_unique_package_paths(
        get_executable_path(),
        *get_user_config_dirs(''),
        *get_system_config_dirs(''),
        containing_folder='yt-dlp-plugins')

    # Load from PYTHONPATH folders
    yield from map(Path, sys.path)


class PluginFinder(importlib.abc.MetaPathFinder):
    """
    This class provides one or multiple namespace packages.
    It searches in sys.path and yt-dlp config folders for
    the existing subdirectories from which the modules can be imported
    """

    def __init__(self, *packages):
        self._zip_content_cache = {}
        self.packages = set(itertools.chain.from_iterable(
            itertools.accumulate(name.split('.'), lambda a, b: '.'.join((a, b)))
            for name in packages))

    def search_locations(self, fullname):
        candidate_locations = itertools.chain.from_iterable(
            default_plugin_paths() if candidate is ...
            else Path(candidate).iterdir()
            for candidate in plugin_dirs.get((..., )))

        parts = Path(*fullname.split('.'))
        locations = dict()
        for path in dict.fromkeys(candidate_locations):
            candidate = path / parts
            # print(candidate)
            if candidate.is_dir():
                locations[candidate] = None
            elif path.name and any(path.with_suffix(suffix).is_file() for suffix in {'.zip', '.egg', '.whl'}):
                if parts in dirs_in_zip(path):
                    locations[candidate] = None

        return list(map(str, locations))

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.packages:
            return None

        search_locations = self.search_locations(fullname)
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
    return inspect.getmembers(module, lambda obj: (
        inspect.isclass(obj)
        and obj.__name__.endswith(suffix)
        and obj.__module__.startswith(module_name)
        and not obj.__name__.startswith('_')
        and obj.__name__ in getattr(module, '__all__', [obj.__name__])))


def load_plugins(plugin_type: PluginType):
    destination, plugin_destination = _plugin_type_lookup[plugin_type]
    name, suffix = plugin_type.value
    classes = {}

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
            write_string(f'Error while importing module {module_name!r}\n{traceback.format_exc(limit=-1)}')
            continue
        classes.update(load_module(module, module_name, suffix))

    # Compat: old plugin system using __init__.py
    # Note: plugins imported this way do not show up in directories()
    # nor are considered part of the yt_dlp_plugins namespace package
    if ... in plugin_dirs.get((..., )):
        with contextlib.suppress(FileNotFoundError):
            spec = importlib.util.spec_from_file_location(
                name, Path(get_executable_path(), COMPAT_PACKAGE_NAME, name, '__init__.py'))
            plugins = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = plugins
            spec.loader.exec_module(plugins)
            classes.update(load_module(plugins, spec.name, suffix))

    # __init_subclass__ was removed so we manually add overrides
    for name, klass in classes.items():
        plugin_name = getattr(klass, '_plugin_name', None)
        if not plugin_name:
            continue

        # FIXME: Most likely something wrong here
        mro = inspect.getmro(klass)
        super_class = klass.__wrapped__ = mro[mro.index(klass) + 1]
        klass.PLUGIN_NAME, klass.ie_key = plugin_name, super_class.ie_key
        klass.IE_NAME = f'{super_class.IE_NAME}+{plugin_name}'
        while getattr(super_class, '__wrapped__', None):
            super_class = super_class.__wrapped__
        setattr(sys.modules[super_class.__module__], super_class.__name__, klass)
        plugin_overrides.get()[super_class].append(klass)

    # Add the classes into the global plugin lookup
    plugin_destination.set(classes)
    # We want to prepend to the main lookup
    current = destination.get()
    result = merge_dicts(classes, current)
    destination.set(result)

    return classes


def load_all_plugin_types():
    for plugin_type in PluginType:
        load_plugins(plugin_type)


sys.meta_path.insert(0, PluginFinder(f'{PACKAGE_NAME}.extractor', f'{PACKAGE_NAME}.postprocessor'))

__all__ = ['directories', 'load_plugins', 'load_all_plugin_types', 'PACKAGE_NAME', 'COMPAT_PACKAGE_NAME']
