import contextlib
import importlib
import importlib.machinery
import importlib.util
import importlib.abc
import inspect
import itertools
import pkgutil
import re
import sys
import traceback
import zipimport
from pathlib import Path
from zipfile import ZipFile

from .utils import (
    write_string,
    get_user_config_dirs,
    get_system_config_dirs,
    get_executable_path
)

PACKAGE_NAME = 'ytdlp_plugins'
_INITIALIZED = False


class PluginLoader(importlib.abc.Loader):
    """ Dummy loader for virtual namespace packages """

    def exec_module(self, module):
        return None


class PluginFinder(importlib.abc.MetaPathFinder):
    """
    This class provides one or multiple namespace packages
    it searches in sys.path and yt-dlp config folders
    for the existing subdirectories from which the modules can be imported
    """

    def __init__(self, *packages):
        self.packages = set()
        self._zip_content_cache = {}

        for name in packages:
            self.packages.update(self.partition(name))

    @staticmethod
    def partition(name):
        yield from itertools.accumulate(name.split('.'), lambda a, b: '.'.join((a, b)))

    def zip_has_dir(self, archive, path):
        if archive not in self._zip_content_cache:
            self._zip_content_cache[archive] = [Path(name) for name in ZipFile(archive).namelist()]
        return any(path in file.parents for file in self._zip_content_cache[archive])

    def search_locations(self, fullname):
        # Also load plugin packages from standard config folders
        search_locations = []
        for config_dir in map(Path, get_user_config_dirs('yt-dlp') + get_system_config_dirs('yt-dlp')):
            plugin_dir = config_dir / 'plugins'
            if not plugin_dir.is_dir():
                continue
            search_locations.extend(plugin_dir / d for d in plugin_dir.iterdir())
        search_locations.extend([Path(path) for path in sys.path])  # PYTHONPATH

        # Required for pyinstaller/py2exe to find plugins in the executable directory
        search_locations.append(Path(get_executable_path()))

        parts = Path(*fullname.split('.'))
        locations = set()
        for path in dict.fromkeys(search_locations):
            candidate = path / parts
            if candidate.is_dir():
                locations.add(str(candidate))
            elif path.name and any(path.with_suffix(suffix).is_file() for suffix in {'.zip', '.egg', '.whl'}):
                with contextlib.suppress(FileNotFoundError):
                    if self.zip_has_dir(path, parts):
                        locations.add(str(candidate))

        return list(locations)

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
        self._zip_content_cache.clear()
        for package in self.packages:
            if package in sys.modules:
                del sys.modules[package]


def initialize():
    global _INITIALIZED
    if _INITIALIZED:
        return

    sys.meta_path.insert(
        0, PluginFinder(f'{PACKAGE_NAME}.extractor', f'{PACKAGE_NAME}.postprocessor'))
    _INITIALIZED = True


def directories():
    spec = importlib.util.find_spec(PACKAGE_NAME)
    return spec.submodule_search_locations if spec else []


def iter_modules(subpackage):
    fullname = f'{PACKAGE_NAME}.{subpackage}'
    with contextlib.suppress(ModuleNotFoundError):
        pkg = importlib.import_module(fullname)
        yield from pkgutil.iter_modules(path=pkg.__path__, prefix=f'{fullname}.')


def load_plugins(name, suffix, namespace=None):
    classes = {}
    namespace = namespace or {}

    def gen_predicate(package_name, module):
        def check_predicate(obj):
            return (inspect.isclass(obj)
                    and obj.__name__.endswith(suffix)
                    and obj.__module__.startswith(package_name)
                    and not obj.__name__.startswith('_')
                    and obj.__name__ in getattr(module, '__all__', [obj.__name__]))

        return check_predicate

    for finder, module_name, is_pkg in iter_modules(name):
        if re.match(r'^(\w+\.)*_', module_name):
            continue
        try:
            if sys.version_info < (3, 10) and isinstance(finder, zipimport.zipimporter):
                # zipimporter.load_module() is deprecated in 3.10 and removed in 3.12
                # The exec_module branch below is the replacement for > 3.10
                # See: https://docs.python.org/3/library/zipimport.html#zipimport.zipimporter.exec_module
                module = finder.load_module(module_name)
            else:
                spec = finder.find_spec(module_name)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
        except Exception:
            write_string(f'Error while importing module {module_name!r}\n{traceback.format_exc(limit=-1)}')
            continue

        sys.modules[module_name] = module
        module_classes = dict(inspect.getmembers(module, gen_predicate(module_name, module)))
        name_collisions = (
            set(classes.keys()) | set(namespace.keys())) & set(module_classes.keys())
        classes.update({key: value for key, value in module_classes.items()
                        if key not in name_collisions})

    namespace.update(classes)
    return classes


initialize()
