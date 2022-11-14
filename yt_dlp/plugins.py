import contextlib
import importlib
import inspect
import itertools
import pkgutil
import shutil
import sys
import os
import traceback
import zipimport
from pathlib import Path
from zipfile import ZipFile

from .utils import write_string, get_config_dirs

PACKAGE_NAME = 'ytdlp_plugins'
_INITIALIZED = False


class PluginLoader(importlib.abc.Loader):
    """ Dummy loader for virtual namespace packages """

    def exec_module(self, module):
        return None


class PluginFinder(importlib.abc.MetaPathFinder):
    """
    This class provides one or multiple namespace packages
    it searches in sys.path for the existing subdirectories
    from which the modules can be imported
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
            self._zip_content_cache[archive] = \
                [Path(name) for name in ZipFile(archive).namelist()]
        return any(path in file.parents for file in self._zip_content_cache[archive])

    def search_locations(self, fullname):
        parts = fullname.split('.')
        locations = []

        # Also load plugin packages from standard config folders
        config_locations = []
        for config_dir in get_config_dirs('yt-dlp'):
            plugin_dir = os.path.join(config_dir, 'plugins')
            if not os.path.isdir(plugin_dir):
                continue
            config_locations.extend(os.path.join(plugin_dir, d) for d in os.listdir(plugin_dir))

        for path in map(Path, dict.fromkeys(sys.path+config_locations).keys()):
            candidate = path.joinpath(*parts)
            if candidate.is_dir():
                locations.append(str(candidate))
            elif path.is_file() and path.suffix in {'.zip', '.egg', '.whl'}:
                with contextlib.suppress(FileNotFoundError):
                    if self.zip_has_dir(path, Path(*parts)):
                        locations.append(str(candidate))

        return locations

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

    # FIXME: https://github.com/yt-dlp/yt-dlp/pull/1393/files#r742829806
    # are we running from PyInstaller single executable?
    # then copy the plugin directory if exist
    root = Path(sys.executable).parent
    meipass = Path(getattr(sys, '_MEIPASS', root))
    if getattr(sys, 'frozen', False) and root != meipass:
        try:
            shutil.copytree(root / PACKAGE_NAME, meipass / PACKAGE_NAME, dirs_exist_ok=True)
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(exc, file=sys.stderr)

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


def load_plugins(name, suffix, namespace):
    classes = {}

    def gen_predicate(package_name):
        def check_predicate(obj):
            return (inspect.isclass(obj)
                    and obj.__name__.endswith(suffix)
                    and obj.__module__.startswith(package_name)
                    and not obj.__name__.startswith('_'))

        return check_predicate

    for finder, module_name, is_pkg in iter_modules(name):
        try:
            if isinstance(finder, zipimport.zipimporter):
                module = finder.load_module(module_name)
            else:
                spec = finder.find_spec(module_name)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
        except Exception:
            write_string(f'Error while importing module {module_name!r}\n{traceback.format_exc(limit=-1)}')
            traceback.print_exc(limit=-1)
            continue

        sys.modules[module_name] = module
        module_classes = dict(inspect.getmembers(module, gen_predicate(module_name)))
        name_collisions = (
            set(classes.keys()) | set(namespace.keys())) & set(module_classes.keys())
        classes.update({key: value for key, value in module_classes.items()
                        if key not in name_collisions})

    namespace.update(classes)
    return classes


initialize()
