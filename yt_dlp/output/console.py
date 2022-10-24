import ctypes
import sys

from .hoodoo import BEL, CSI
from ..utils import supports_terminal_sequences, write_string

_console_initialized = False
_console_allow_title_change = False
_console = None
_console_encoding = None


def init(windows, encoding=None, allow_title_change=False):
    global _console_initialized
    global _console_allow_title_change
    global _console
    global _console_encoding

    _console_allow_title_change = allow_title_change

    for stream in (sys.stderr, sys.stdout):
        if supports_terminal_sequences(stream):
            _console_initialized = True
            _console = stream
            _console_encoding = encoding
            return

    if windows:
        _console_initialized = True
        _console = False


def send_code(code):
    if not _console_initialized or not _console:
        return

    write_string(code, _console, _console_encoding)


def change_title(message):
    if not _console_initialized or not _console_allow_title_change:
        return

    if _console:
        send_code(f'{CSI}0;{message}{BEL}')
        return

    if hasattr(ctypes, 'windll') and ctypes.windll.kernel32.GetConsoleWindow():
        ctypes.windll.kernel32.SetConsoleTitleW(message)


def save_title():
    send_code(f'{CSI}22;0t')


def restore_title():
    send_code(f'{CSI}23;0t')
