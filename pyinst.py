#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings

from bundle.pyinstaller import main

warnings.warn(DeprecationWarning('`pyinst.py` is deprecated. Use `bundle.pyinstaller` instead'))

if __name__ == '__main__':
    main()
