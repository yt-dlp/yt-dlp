import importlib
import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__)), 'testdata')
sys.path.append(str(TEST_DATA_DIR))
importlib.invalidate_caches()

from yt_dlp.plugins import PACKAGE_NAME, PluginType, directories, load_plugins
from yt_dlp._globals import extractors, postprocessors


class TestPlugins(unittest.TestCase):

    TEST_PLUGIN_DIR = TEST_DATA_DIR / PACKAGE_NAME

    def test_directories_containing_plugins(self):
        self.assertIn(self.TEST_PLUGIN_DIR, map(Path, directories()))

    def test_extractor_classes(self):
        for module_name in tuple(sys.modules):
            if module_name.startswith(f'{PACKAGE_NAME}.extractor'):
                del sys.modules[module_name]
        plugins_ie = load_plugins(PluginType.EXTRACTORS)

        self.assertIn(f'{PACKAGE_NAME}.extractor.normal', sys.modules.keys())
        self.assertIn('NormalPluginIE', plugins_ie.keys())

        # don't load modules with underscore prefix
        self.assertFalse(
            f'{PACKAGE_NAME}.extractor._ignore' in sys.modules,
            'loaded module beginning with underscore')
        self.assertNotIn('IgnorePluginIE', plugins_ie.keys())

        # Don't load extractors with underscore prefix
        self.assertNotIn('_IgnoreUnderscorePluginIE', plugins_ie.keys())

        # Don't load extractors not specified in __all__ (if supplied)
        self.assertNotIn('IgnoreNotInAllPluginIE', plugins_ie.keys())
        self.assertIn('InAllPluginIE', plugins_ie.keys())

    def test_postprocessor_classes(self):
        plugins_pp = load_plugins(PluginType.POSTPROCESSORS)
        self.assertIn('NormalPluginPP', plugins_pp.keys())

    def test_importing_zipped_module(self):
        zip_path = TEST_DATA_DIR / 'zipped_plugins.zip'
        shutil.make_archive(str(zip_path)[:-4], 'zip', str(zip_path)[:-4])
        sys.path.append(str(zip_path))  # add zip to search paths
        importlib.invalidate_caches()  # reset the import caches

        try:
            for plugin_type in ('extractor', 'postprocessor'):
                package = importlib.import_module(f'{PACKAGE_NAME}.{plugin_type}')
                self.assertIn(zip_path / PACKAGE_NAME / plugin_type, map(Path, package.__path__))

            plugins_ie = load_plugins(PluginType.EXTRACTORS)
            self.assertIn('ZippedPluginIE', plugins_ie.keys())

            plugins_pp = load_plugins(PluginType.POSTPROCESSORS)
            self.assertIn('ZippedPluginPP', plugins_pp.keys())

        finally:
            sys.path.remove(str(zip_path))
            os.remove(zip_path)
            importlib.invalidate_caches()  # reset the import caches

    def test_reloading_plugins(self):
        reload_plugins_path = TEST_DATA_DIR / 'reload_plugins'

        for plugin_type in ('extractor', 'postprocessor'):
            package = importlib.import_module(f'{PACKAGE_NAME}.{plugin_type}')
        load_plugins(PluginType.EXTRACTORS)
        load_plugins(PluginType.POSTPROCESSORS)

        # Remove default folder and add reload_plugin path
        sys.path.remove(str(TEST_DATA_DIR))
        sys.path.append(str(reload_plugins_path))
        importlib.invalidate_caches()
        try:
            for plugin_type in ('extractor', 'postprocessor'):
                package = importlib.import_module(f'{PACKAGE_NAME}.{plugin_type}')
                self.assertIn(reload_plugins_path / PACKAGE_NAME / plugin_type, map(Path, package.__path__))

            plugins_ie = load_plugins(PluginType.EXTRACTORS)
            self.assertIn('NormalPluginIE', plugins_ie.keys())
            self.assertTrue(
                plugins_ie['NormalPluginIE'].REPLACED,
                msg='Reloading has not replaced original extractor plugin')
            self.assertTrue(
                extractors.get()['NormalPluginIE'].REPLACED,
                msg='Reloading has not replaced original extractor plugin globally')

            plugins_pp = load_plugins(PluginType.POSTPROCESSORS)
            self.assertIn('NormalPluginPP', plugins_pp.keys())
            self.assertTrue(plugins_pp['NormalPluginPP'].REPLACED,
                            msg='Reloading has not replaced original postprocessor plugin')
            self.assertTrue(
                postprocessors.get()['NormalPluginPP'].REPLACED,
                msg='Reloading has not replaced original postprocessor plugin globally')

        finally:
            sys.path.remove(str(reload_plugins_path))
            sys.path.append(str(TEST_DATA_DIR))
            importlib.invalidate_caches()


if __name__ == '__main__':
    unittest.main()
