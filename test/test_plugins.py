# coding: utf-8
import importlib
import sys
import unittest
from importlib import invalidate_caches
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

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

    def test_importing_zipped_module(self):
        """
        create a zip file with plugins and check if it can be imported
        """
        with TemporaryDirectory() as tmp:
            zipmodule_path = Path(tmp, "plugins.zip")
            with ZipFile(zipmodule_path, mode="w") as zipmodule:
                for file in self.SAMPLE_PLUGIN_DIR.rglob("*.py"):
                    zipmodule.write(file, arcname=file.relative_to(self.SAMPLE_PLUGIN_DIR.parent))

            sys.path.append(str(zipmodule_path))  # add zip to search paths
            invalidate_caches()  # reset the import caches

            for plugin_type in ("extractor", "postprocessor"):
                package = importlib.import_module(f"{PACKAGE_NAME}.{plugin_type}")
                self.assertIn(zipmodule_path / PACKAGE_NAME / plugin_type, map(Path, package.__path__))


if __name__ == "__main__":
    unittest.main()
