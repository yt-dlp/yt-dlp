# flake8: noqa: F405
from re import *  # F403

from .compat_utils import passthrough_module

passthrough_module(__name__, 're')
del passthrough_module

try:
    Pattern  # >= 3.7
except NameError:
    Pattern = type(compile(''))


try:
    Match  # >= 3.7
except NameError:
    Match = type(compile('').match(''))
