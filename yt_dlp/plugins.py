import importlib
import sys
import traceback
from contextlib import suppress
from inspect import getmembers, isclass
from itertools import accumulate
from pathlib import Path
from pkgutil import iter_modules as pkgutil_iter_modules
from shutil import copytree
from zipfile import ZipFile
from zipimport import zipimporter

PACKAGE_NAME = 'ytdlp_plugins'
_INITIALIZED = False


class PluginLoader:
    ''' Dummy loader for virtual namespace packages '''
    @classmethod
    def create_module(cls, spec):
        pass

    @classmethod
    def exec_module(cls, module):
        pass


class PluginFinder(importlib.abc.MetaPathFinder):
    '''
    This class provides one or multiple namespace packages
    it searches in sys.path for the existing subdirectories
    from which the modules can be imported
    '''
    @staticmethod
    def partition(name):
        yield from accumulate(name.split('.'), lambda a, b: '.'.join((a, b)))

    def __init__(self, *packages):
        self.packages = set()
        for name in packages:
            self.packages.update(self.partition(name))

    @staticmethod
    def search_locations(fullname):
        parts = fullname.split('.')
        loc = []
        for path in map(Path, sys.path):
            candidate = path.joinpath(*parts)
            if candidate.is_dir():
                loc.append(str(candidate))
            elif path.is_file() and path.suffix in {'.zip', '.egg', '.whl'}:
                with suppress(FileNotFoundError):
                    zipfile = ZipFile(path, 'r')
                    if any(
                        name.startswith('/'.join((*parts, '')))
                        for name in zipfile.namelist()
                    ):
                        loc.append(str(candidate))

        return loc

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.packages:
            return None

        search_locations = self.search_locations(fullname)
        if not search_locations:
            return None

        spec = importlib.machinery.ModuleSpec(fullname, PluginLoader, is_package=True)
        spec.submodule_search_locations = search_locations
        return spec


def initialize():
    global _INITIALIZED
    if _INITIALIZED:
        return

    # are we running from PyInstaller single executable?
    # then copy the plugin directory if exist
    root = Path(sys.executable).parent
    meipass = Path(getattr(sys, '_MEIPASS', '.'))
    if getattr(sys, 'frozen', False) and root != meipass:
        try:
            copytree(root / PACKAGE_NAME, meipass / PACKAGE_NAME, dirs_exist_ok=False)
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(exc, file=sys.stderr)

    sys.meta_path.insert(
        0, PluginFinder(f'{PACKAGE_NAME}.extractor', f'{PACKAGE_NAME}.postprocessor'))
    _INITIALIZED = True


def iter_modules(subpackage):
    fullname = f'{PACKAGE_NAME}.{subpackage}'
    with suppress(ModuleNotFoundError):
        pkg = importlib.import_module(fullname)
        yield from pkgutil_iter_modules(path=pkg.__path__, prefix=f'{fullname}.')


def load_plugins(name, suffix, namespace):
    classes = {}

    def predicate(package_name):
        def check_pred(obj):
            return (isclass(obj)
                    and obj.__name__.endswith(suffix)
                    and obj.__module__.startswith(package_name))

        return check_pred

    for finder, module_name, is_pkg in iter_modules(name):
        try:
            if isinstance(finder, zipimporter):
                module = finder.load_module(module_name)
            else:
                spec = finder.find_spec(module_name)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
        except Exception:
            print(f"Error while importing module '{module_name}'", file=sys.stderr)
            traceback.print_exc(limit=-1)
            continue

        sys.modules[module_name] = module
        module_classes = dict(getmembers(module, predicate(module_name)))
        name_collisons = (set(classes.keys()) | set(namespace.keys())) & set(
            module_classes.keys()
        )
        classes.update(
            {
                key: value
                for key, value in module_classes.items()
                if key not in name_collisons
            }
        )

    namespace.update(classes)
    return classes


def directories():
    spec = importlib.util.find_spec(PACKAGE_NAME)
    return spec.submodule_search_locations if spec else []


initialize()
