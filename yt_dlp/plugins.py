import contextlib
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

from .utils import (
    Config,
    get_executable_path,
    get_system_config_dirs,
    get_user_config_dirs,
    orderedSet,
    write_string,
)

PACKAGE_NAME = 'yt_dlp_plugins'
COMPAT_PACKAGE_NAME = 'ytdlp_plugins'


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
    return set()


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
        candidate_locations = []

        def _get_package_paths(*root_paths, containing_folder='plugins'):
            for config_dir in orderedSet(map(Path, root_paths), lazy=True):
                with contextlib.suppress(OSError):
                    yield from (config_dir / containing_folder).iterdir()

        # Load from yt-dlp config folders
        candidate_locations.extend(_get_package_paths(
            *get_user_config_dirs('yt-dlp'),
            *get_system_config_dirs('yt-dlp'),
            containing_folder='plugins'))

        # Load from yt-dlp-plugins folders
        candidate_locations.extend(_get_package_paths(
            get_executable_path(),
            *get_user_config_dirs(''),
            *get_system_config_dirs(''),
            containing_folder='yt-dlp-plugins'))

        candidate_locations.extend(map(Path, sys.path))  # PYTHONPATH
        with contextlib.suppress(ValueError):  # Added when running __main__.py directly
            candidate_locations.remove(Path(__file__).parent)

        # TODO(coletdjnz): remove when plugin globals system is implemented
        if Config._plugin_dirs:
            candidate_locations.extend(_get_package_paths(
                *Config._plugin_dirs,
                containing_folder=''))

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
    return inspect.getmembers(module, lambda obj: (
        inspect.isclass(obj)
        and obj.__name__.endswith(suffix)
        and obj.__module__.startswith(module_name)
        and not obj.__name__.startswith('_')
        and obj.__name__ in getattr(module, '__all__', [obj.__name__])))


def load_plugins(name, suffix):
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
            write_string(f'Error while importing module {module_name!r}\n{traceback.format_exc(limit=-1)}')
            continue
        classes.update(load_module(module, module_name, suffix))

    # Compat: old plugin system using __init__.py
    # Note: plugins imported this way do not show up in directories()
    # nor are considered part of the yt_dlp_plugins namespace package
    with contextlib.suppress(FileNotFoundError):
        spec = importlib.util.spec_from_file_location(
            name, Path(get_executable_path(), COMPAT_PACKAGE_NAME, name, '__init__.py'))
        plugins = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = plugins
        spec.loader.exec_module(plugins)
        classes.update(load_module(plugins, spec.name, suffix))

    return classes


sys.meta_path.insert(0, PluginFinder(f'{PACKAGE_NAME}.extractor', f'{PACKAGE_NAME}.postprocessor'))

__all__ = ['COMPAT_PACKAGE_NAME', 'PACKAGE_NAME', 'directories', 'load_plugins']
