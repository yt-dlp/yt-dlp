# flake8: noqa
import os
import sys

# Import extractors plugins if using Bundle App
if hasattr(sys, "frozen"):
    # for load_module extractor (plugins)
    HERE = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(HERE))

# ⚠ Don't use relative imports beyond top-level package
from .sample import SamplePluginIE
