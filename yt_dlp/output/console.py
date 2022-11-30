import sys

from .hoodoo import BEL, CSI, TermCode
from ..utils import supports_terminal_sequences, write_string


class Console:
    SAVE_TITLE = TermCode(f'{CSI}22;0t')
    RESTORE_TITLE = TermCode(f'{CSI}23;0t')

    def __init__(self, encoding=None, allow_title_change=False):
        self.initialized = False
        self.stream = None
        self._stream_encoding = encoding

        for stream in (sys.stderr, sys.stdout):
            if supports_terminal_sequences(stream):
                self.stream = stream
                self.initialized = True

        self.allow_title_change = allow_title_change
        self._title_func = None

        if not allow_title_change:
            return

        if self.initialized:
            self._title_func = self._change_title_term_sequence
            return

        if sys.platform != 'win32':
            return

        import ctypes
        if not hasattr(ctypes, 'windll'):
            return

        if not ctypes.windll.kernel32.GetConsoleWindow():
            return

        self._title_func = self._change_title_win_api

    def change_title(self, title):
        if self._title_func is None:
            return

        self._title_func(title)

    def send_code(self, code):
        if not self.initialized:
            return

        write_string(code, self.stream, self._stream_encoding)

    def save_title(self):
        if not self.allow_title_change:
            return

        self.send_code(self.SAVE_TITLE)

    def restore_title(self):
        if not self.allow_title_change:
            return

        self.send_code(self.RESTORE_TITLE)

    def _change_title_term_sequence(self, title):
        self.send_code(f'{CSI}0;{title}{BEL}')

    def _change_title_win_api(self, title):
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW(title)
