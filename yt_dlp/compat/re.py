# flake8: noqa: F405

from re import *  # F403

try:
    Pattern  # >= 3.7
except NameError:
    Pattern = type(compile(''))


try:
    Match  # >= 3.7
except NameError:
    Match = type(compile('').match(''))
