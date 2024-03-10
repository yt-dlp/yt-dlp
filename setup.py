#!/usr/bin/env python3

# Allow execution from anywhere
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings


if sys.argv[1:2] == ['py2exe']:
    warnings.warn(DeprecationWarning('`setup.py py2exe` is deprecated and will be removed in a future version. '
                                     'Use `bundle.py2exe` instead'))

    import bundle.py2exe

    bundle.py2exe.main()

elif 'build_lazy_extractors' in sys.argv:
    warnings.warn(DeprecationWarning('`setup.py build_lazy_extractors` is deprecated and will be removed in a future version. '
                                     'Use `devscripts.make_lazy_extractors` instead'))

    import subprocess

    os.chdir(sys.path[0])
    print('running build_lazy_extractors')
    subprocess.run([sys.executable, 'devscripts/make_lazy_extractors.py'])

else:

    print(
        'ERROR: Building by calling `setup.py` is deprecated. '
        'Use a build frontend like `build` instead. ',
        'Refer to  https://build.pypa.io  for more info', file=sys.stderr)
    sys.exit(1)
