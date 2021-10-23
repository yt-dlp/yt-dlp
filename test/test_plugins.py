# coding: utf-8
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parents[1].absolute()
sys.path.insert(0, str(ROOT_DIR))

from yt_dlp.plugins import PACKAGE_NAME, directories, load_plugins


class TestPlugins(unittest.TestCase):
    SAMPLE_PLUGIN_DIR = ROOT_DIR / PACKAGE_NAME

    def test_plugin_directory_structure(self):
        self.assertFalse(self.SAMPLE_PLUGIN_DIR.joinpath("__init__.py").exists())
        self.assertTrue(self.SAMPLE_PLUGIN_DIR.joinpath("extractor").is_dir())
        self.assertFalse(self.SAMPLE_PLUGIN_DIR.joinpath("extractor", "__init__.py").exists())
        self.assertTrue(self.SAMPLE_PLUGIN_DIR.joinpath("postprocessor").is_dir())
        self.assertFalse(self.SAMPLE_PLUGIN_DIR.joinpath("postprocessor", "__init__.py").exists())

    def test_directories_containing_plugins(self):
        plugin_dirs = {Path(path) for path in directories()}
        self.assertIn(self.SAMPLE_PLUGIN_DIR, plugin_dirs)

    def test_extractor_classes(self):
        plugins_ie = load_plugins("extractor", "IE", {})
        self.assertIn("SamplePluginIE", plugins_ie.keys())

    def test_postprocessor_classes(self):
        plugins_pp = load_plugins("postprocessor", "PP", {})
        self.assertIn("SamplePluginPP", plugins_pp.keys())


if __name__ == "__main__":
    unittest.main()
