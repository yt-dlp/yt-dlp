import sys
import warnings


if sys.argv[1:2] != ['py2exe']:
    print(
        'ERROR: Building by calling `setup.py` is deprecated. '
        'Use a build frontend like `build` instead. ',
        'Refer to  https://build.pypa.io  for more info', file=sys.stderr)
    sys.exit(1)

warnings.warn(DeprecationWarning('`setup.py py2exe` is deprecated. Use `bundle.py2exe` instead'))

import bundle.py2exe

bundle.py2exe.main()
