import contextlib
import dataclasses
import functools
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
    Indirect,
    plugin_dirs,
    all_plugins_loaded,
    plugin_specs,
)

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


# Please Note: Due to necessary changes and the complex nature involved,
# no backwards compatibility is guaranteed for the plugin system API.
# However, we will still try our best.

__all__ = [
    'COMPAT_PACKAGE_NAME',
    'PACKAGE_NAME',
    'PluginSpec',
    'directories',
    'load_all_plugins',
    'load_plugins',
    'register_plugin_spec',
]


@dataclasses.dataclass
class PluginSpec:
    module_name: str
    suffix: str
    destination: Indirect
    plugin_destination: Indirect


class PluginLoader(importlib.abc.Loader):
    """Dummy loader for virtual namespace packages"""

    def exec_module(self, module):
        return None


@functools.cache
def dirs_in_zip(archive):
    try:
        with ZipFile(archive) as zip_:
            return set(itertools.chain.from_iterable(
                Path(file).parents for file in zip_.namelist()))
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

    # Load from PYTHONPATH directories
    yield from (path for path in map(Path, sys.path) if path != _BASE_PACKAGE_PATH)


def candidate_plugin_paths(candidate):
    candidate_path = Path(candidate)
    if not candidate_path.is_dir():
        raise ValueError(f'Invalid plugin directory: {candidate_path}')
    yield from candidate_path.iterdir()


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
                for name in packages))

    def search_locations(self, fullname):
        candidate_locations = itertools.chain.from_iterable(
            default_plugin_paths() if candidate == 'default' else candidate_plugin_paths(candidate)
            for candidate in plugin_dirs.value
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
            # Prevent using built-in meta finders for searching plugins.
            raise ModuleNotFoundError(fullname)

        spec = importlib.machinery.ModuleSpec(fullname, PluginLoader(), is_package=True)
        spec.submodule_search_locations = search_locations
        return spec

    def invalidate_caches(self):
        dirs_in_zip.cache_clear()
        for package in self.packages:
            if package in sys.modules:
                del sys.modules[package]


def directories():
    with contextlib.suppress(ModuleNotFoundError):
        if spec := importlib.util.find_spec(PACKAGE_NAME):
            return list(spec.submodule_search_locations)
    return []


def iter_modules(subpackage):
    fullname = f'{PACKAGE_NAME}.{subpackage}'
    with contextlib.suppress(ModuleNotFoundError):
        pkg = importlib.import_module(fullname)
        yield from pkgutil.iter_modules(path=pkg.__path__, prefix=f'{fullname}.')


def get_regular_classes(module, module_name, suffix):
    # Find standard public plugin classes (not overrides)
    return inspect.getmembers(module, lambda obj: (
        inspect.isclass(obj)
        and obj.__name__.endswith(suffix)
        and obj.__module__.startswith(module_name)
        and not obj.__name__.startswith('_')
        and obj.__name__ in getattr(module, '__all__', [obj.__name__])
        and getattr(obj, 'PLUGIN_NAME', None) is None
    ))


def load_plugins(plugin_spec: PluginSpec):
    name, suffix = plugin_spec.module_name, plugin_spec.suffix
    regular_classes = {}
    if os.environ.get('YTDLP_NO_PLUGINS') or not plugin_dirs.value:
        return regular_classes

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
        regular_classes.update(get_regular_classes(module, module_name, suffix))

    # Compat: old plugin system using __init__.py
    # Note: plugins imported this way do not show up in directories()
    # nor are considered part of the yt_dlp_plugins namespace package
    if 'default' in plugin_dirs.value:
        with contextlib.suppress(FileNotFoundError):
            spec = importlib.util.spec_from_file_location(
                name,
                Path(get_executable_path(), COMPAT_PACKAGE_NAME, name, '__init__.py'),
            )
            plugins = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = plugins
            spec.loader.exec_module(plugins)
            regular_classes.update(get_regular_classes(plugins, spec.name, suffix))

    # Add the classes into the global plugin lookup for that type
    plugin_spec.plugin_destination.value = regular_classes
    # We want to prepend to the main lookup for that type
    plugin_spec.destination.value = merge_dicts(regular_classes, plugin_spec.destination.value)

    return regular_classes


def load_all_plugins():
    for plugin_spec in plugin_specs.value.values():
        load_plugins(plugin_spec)
    all_plugins_loaded.value = True


def register_plugin_spec(plugin_spec: PluginSpec):
    # If the plugin spec for a module is already registered, it will not be added again
    if plugin_spec.module_name not in plugin_specs.value:
        plugin_specs.value[plugin_spec.module_name] = plugin_spec
        sys.meta_path.insert(0, PluginFinder(f'{PACKAGE_NAME}.{plugin_spec.module_name}'))
