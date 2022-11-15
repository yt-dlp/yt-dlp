# coding: utf-8
import importlib
import sys
import unittest
from importlib import invalidate_caches
from pathlib import Path
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__)), 'testdata')
sys.path.append(str(TEST_DATA_DIR))
invalidate_caches()

from yt_dlp.plugins import PACKAGE_NAME, directories, load_plugins


class TestPlugins(unittest.TestCase):

    TEST_PLUGIN_DIR = TEST_DATA_DIR / f'{PACKAGE_NAME}'

    def test_plugin_directory_structure(self):
        # TODO: doesn't test much?
        self.assertFalse(self.TEST_PLUGIN_DIR.joinpath('__init__.py').exists())
        self.assertTrue(self.TEST_PLUGIN_DIR.joinpath('extractor').is_dir())
        self.assertFalse(self.TEST_PLUGIN_DIR.joinpath('extractor', '__init__.py').exists())
        self.assertTrue(self.TEST_PLUGIN_DIR.joinpath('postprocessor').is_dir())
        self.assertFalse(self.TEST_PLUGIN_DIR.joinpath('postprocessor', '__init__.py').exists())

    def test_directories_containing_plugins(self):
        plugin_dirs = {Path(path) for path in directories()}
        self.assertIn(self.TEST_PLUGIN_DIR, plugin_dirs)

    def test_extractor_classes(self):
        for module_name in tuple(sys.modules):
            if module_name.startswith(f'{PACKAGE_NAME}.extractor'):
                del sys.modules[module_name]
        plugins_ie = load_plugins('extractor', 'IE')
        self.assertIn(f'{PACKAGE_NAME}.extractor.normal', sys.modules.keys())
        self.assertIn('NormalPluginIE', plugins_ie.keys())
        # don't load modules with underscore prefix
        self.assertFalse(
            f'{PACKAGE_NAME}.extractor._ignore' in sys.modules.keys(),
            'loaded module beginning with underscore',
        )
        self.assertNotIn('IgnorePluginIE', plugins_ie.keys())

    def test_postprocessor_classes(self):
        plugins_pp = load_plugins('postprocessor', 'PP')
        self.assertIn('NormalPluginPP', plugins_pp.keys())

    def test_importing_zipped_module(self):
        zip_path = TEST_DATA_DIR / 'zipped_plugins.zip'

        sys.path.append(str(zip_path))  # add zip to search paths
        invalidate_caches()  # reset the import caches

        for plugin_type in ('extractor', 'postprocessor'):
            package = importlib.import_module(f'{PACKAGE_NAME}.{plugin_type}')
            self.assertIn(zip_path / PACKAGE_NAME / plugin_type, map(Path, package.__path__))

        plugins_ie = load_plugins('extractor', 'IE')
        self.assertIn('ZippedPluginIE', plugins_ie.keys())

        plugins_pp = load_plugins('postprocessor', 'PP')
        self.assertIn('ZippedPluginPP', plugins_pp.keys())

        sys.path.remove(str(zip_path))
        invalidate_caches()  # reset the import caches


if __name__ == '__main__':
    unittest.main()
