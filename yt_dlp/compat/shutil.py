# flake8: noqa: F405
from shutil import *  # noqa: F403

from .compat_utils import passthrough_module

passthrough_module(__name__, 'shutil')
del passthrough_module


import sys

if sys.platform.startswith('freebsd'):
    import errno
    import os
    import shutil

    # Workaround for PermissionError when using restricted ACL mode on FreeBSD
    def copy2(src, dst, *args, **kwargs):
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))
        shutil.copyfile(src, dst, *args, **kwargs)
        try:
            shutil.copystat(src, dst, *args, **kwargs)
        except PermissionError as e:
            if e.errno != getattr(errno, 'EPERM', None):
                raise
        return dst

    def move(*args, copy_function=copy2, **kwargs):
        return shutil.move(*args, copy_function=copy_function, **kwargs)
