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

from yt_dlp.plugins import (
    PACKAGE_NAME,
    PluginSpec,
    directories,
    load_plugins,
    load_all_plugins,
    register_plugin_spec,
)

from yt_dlp.globals import (
    extractors,
    postprocessors,
    plugin_dirs,
    plugin_ies,
    plugin_pps,
    all_plugins_loaded,
    plugin_specs,
)


EXTRACTOR_PLUGIN_SPEC = PluginSpec(
    module_name='extractor',
    suffix='IE',
    destination=extractors,
    plugin_destination=plugin_ies,
)

POSTPROCESSOR_PLUGIN_SPEC = PluginSpec(
    module_name='postprocessor',
    suffix='PP',
    destination=postprocessors,
    plugin_destination=plugin_pps,
)


def reset_plugins():
    plugin_ies.value = {}
    plugin_pps.value = {}
    plugin_dirs.value = ['default']
    plugin_specs.value = {}
    all_plugins_loaded.value = False
    # Clearing override plugins is probably difficult
    for module_name in tuple(sys.modules):
        for plugin_type in ('extractor', 'postprocessor'):
            if module_name.startswith(f'{PACKAGE_NAME}.{plugin_type}.'):
                del sys.modules[module_name]

    importlib.invalidate_caches()


class TestPlugins(unittest.TestCase):

    TEST_PLUGIN_DIR = TEST_DATA_DIR / PACKAGE_NAME

    def setUp(self):
        reset_plugins()

    def tearDown(self):
        reset_plugins()

    def test_directories_containing_plugins(self):
        self.assertIn(self.TEST_PLUGIN_DIR, map(Path, directories()))

    def test_extractor_classes(self):
        plugins_ie = load_plugins(EXTRACTOR_PLUGIN_SPEC)

        self.assertIn(f'{PACKAGE_NAME}.extractor.normal', sys.modules.keys())
        self.assertIn('NormalPluginIE', plugins_ie.keys())

        # don't load modules with underscore prefix
        self.assertFalse(
            f'{PACKAGE_NAME}.extractor._ignore' in sys.modules,
            'loaded module beginning with underscore')
        self.assertNotIn('IgnorePluginIE', plugins_ie.keys())
        self.assertNotIn('IgnorePluginIE', plugin_ies.value)

        # Don't load extractors with underscore prefix
        self.assertNotIn('_IgnoreUnderscorePluginIE', plugins_ie.keys())
        self.assertNotIn('_IgnoreUnderscorePluginIE', plugin_ies.value)

        # Don't load extractors not specified in __all__ (if supplied)
        self.assertNotIn('IgnoreNotInAllPluginIE', plugins_ie.keys())
        self.assertNotIn('IgnoreNotInAllPluginIE', plugin_ies.value)
        self.assertIn('InAllPluginIE', plugins_ie.keys())
        self.assertIn('InAllPluginIE', plugin_ies.value)

        # Don't load override extractors
        self.assertNotIn('OverrideGenericIE', plugins_ie.keys())
        self.assertNotIn('OverrideGenericIE', plugin_ies.value)
        self.assertNotIn('_UnderscoreOverrideGenericIE', plugins_ie.keys())
        self.assertNotIn('_UnderscoreOverrideGenericIE', plugin_ies.value)

    def test_postprocessor_classes(self):
        plugins_pp = load_plugins(POSTPROCESSOR_PLUGIN_SPEC)
        self.assertIn('NormalPluginPP', plugins_pp.keys())
        self.assertIn(f'{PACKAGE_NAME}.postprocessor.normal', sys.modules.keys())
        self.assertIn('NormalPluginPP', plugin_pps.value)

    def test_importing_zipped_module(self):
        zip_path = TEST_DATA_DIR / 'zipped_plugins.zip'
        shutil.make_archive(str(zip_path)[:-4], 'zip', str(zip_path)[:-4])
        sys.path.append(str(zip_path))  # add zip to search paths
        importlib.invalidate_caches()  # reset the import caches

        try:
            for plugin_type in ('extractor', 'postprocessor'):
                package = importlib.import_module(f'{PACKAGE_NAME}.{plugin_type}')
                self.assertIn(zip_path / PACKAGE_NAME / plugin_type, map(Path, package.__path__))

            plugins_ie = load_plugins(EXTRACTOR_PLUGIN_SPEC)
            self.assertIn('ZippedPluginIE', plugins_ie.keys())

            plugins_pp = load_plugins(POSTPROCESSOR_PLUGIN_SPEC)
            self.assertIn('ZippedPluginPP', plugins_pp.keys())

        finally:
            sys.path.remove(str(zip_path))
            os.remove(zip_path)
            importlib.invalidate_caches()  # reset the import caches

    def test_reloading_plugins(self):
        reload_plugins_path = TEST_DATA_DIR / 'reload_plugins'
        load_plugins(EXTRACTOR_PLUGIN_SPEC)
        load_plugins(POSTPROCESSOR_PLUGIN_SPEC)

        # Remove default folder and add reload_plugin path
        sys.path.remove(str(TEST_DATA_DIR))
        sys.path.append(str(reload_plugins_path))
        importlib.invalidate_caches()
        try:
            for plugin_type in ('extractor', 'postprocessor'):
                package = importlib.import_module(f'{PACKAGE_NAME}.{plugin_type}')
                self.assertIn(reload_plugins_path / PACKAGE_NAME / plugin_type, map(Path, package.__path__))

            plugins_ie = load_plugins(EXTRACTOR_PLUGIN_SPEC)
            self.assertIn('NormalPluginIE', plugins_ie.keys())
            self.assertTrue(
                plugins_ie['NormalPluginIE'].REPLACED,
                msg='Reloading has not replaced original extractor plugin')
            self.assertTrue(
                extractors.value['NormalPluginIE'].REPLACED,
                msg='Reloading has not replaced original extractor plugin globally')

            plugins_pp = load_plugins(POSTPROCESSOR_PLUGIN_SPEC)
            self.assertIn('NormalPluginPP', plugins_pp.keys())
            self.assertTrue(plugins_pp['NormalPluginPP'].REPLACED,
                            msg='Reloading has not replaced original postprocessor plugin')
            self.assertTrue(
                postprocessors.value['NormalPluginPP'].REPLACED,
                msg='Reloading has not replaced original postprocessor plugin globally')

        finally:
            sys.path.remove(str(reload_plugins_path))
            sys.path.append(str(TEST_DATA_DIR))
            importlib.invalidate_caches()

    def test_extractor_override_plugin(self):
        load_plugins(EXTRACTOR_PLUGIN_SPEC)

        from yt_dlp.extractor.generic import GenericIE

        self.assertEqual(GenericIE.TEST_FIELD, 'override')
        self.assertEqual(GenericIE.SECONDARY_TEST_FIELD, 'underscore-override')

        self.assertEqual(GenericIE.IE_NAME, 'generic+override+underscore-override')
        importlib.invalidate_caches()
        #  test that loading a second time doesn't wrap a second time
        load_plugins(EXTRACTOR_PLUGIN_SPEC)
        from yt_dlp.extractor.generic import GenericIE
        self.assertEqual(GenericIE.IE_NAME, 'generic+override+underscore-override')

    def test_load_all_plugin_types(self):

        # no plugin specs registered
        load_all_plugins()

        self.assertNotIn(f'{PACKAGE_NAME}.extractor.normal', sys.modules.keys())
        self.assertNotIn(f'{PACKAGE_NAME}.postprocessor.normal', sys.modules.keys())

        register_plugin_spec(EXTRACTOR_PLUGIN_SPEC)
        register_plugin_spec(POSTPROCESSOR_PLUGIN_SPEC)
        load_all_plugins()
        self.assertTrue(all_plugins_loaded.value)

        self.assertIn(f'{PACKAGE_NAME}.extractor.normal', sys.modules.keys())
        self.assertIn(f'{PACKAGE_NAME}.postprocessor.normal', sys.modules.keys())

    def test_no_plugin_dirs(self):
        register_plugin_spec(EXTRACTOR_PLUGIN_SPEC)
        register_plugin_spec(POSTPROCESSOR_PLUGIN_SPEC)

        plugin_dirs.value = []
        load_all_plugins()

        self.assertNotIn(f'{PACKAGE_NAME}.extractor.normal', sys.modules.keys())
        self.assertNotIn(f'{PACKAGE_NAME}.postprocessor.normal', sys.modules.keys())

    def test_set_plugin_dirs(self):
        custom_plugin_dir = str(TEST_DATA_DIR / 'plugin_packages')
        plugin_dirs.value = [custom_plugin_dir]

        load_plugins(EXTRACTOR_PLUGIN_SPEC)

        self.assertIn(f'{PACKAGE_NAME}.extractor.package', sys.modules.keys())
        self.assertIn('PackagePluginIE', plugin_ies.value)

    def test_invalid_plugin_dir(self):
        plugin_dirs.value = ['invalid_dir']
        with self.assertRaises(ValueError):
            load_plugins(EXTRACTOR_PLUGIN_SPEC)

    def test_append_plugin_dirs(self):
        custom_plugin_dir = str(TEST_DATA_DIR / 'plugin_packages')

        self.assertEqual(plugin_dirs.value, ['default'])
        plugin_dirs.value.append(custom_plugin_dir)
        self.assertEqual(plugin_dirs.value, ['default', custom_plugin_dir])

        load_plugins(EXTRACTOR_PLUGIN_SPEC)

        self.assertIn(f'{PACKAGE_NAME}.extractor.package', sys.modules.keys())
        self.assertIn('PackagePluginIE', plugin_ies.value)

    def test_get_plugin_spec(self):
        register_plugin_spec(EXTRACTOR_PLUGIN_SPEC)
        register_plugin_spec(POSTPROCESSOR_PLUGIN_SPEC)

        self.assertEqual(plugin_specs.value.get('extractor'), EXTRACTOR_PLUGIN_SPEC)
        self.assertEqual(plugin_specs.value.get('postprocessor'), POSTPROCESSOR_PLUGIN_SPEC)
        self.assertIsNone(plugin_specs.value.get('invalid'))


if __name__ == '__main__':
    unittest.main()
