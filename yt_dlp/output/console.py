import sys

from .hoodoo import BEL, CSI, TermCode
from .outputs import NULL_OUTPUT, StreamOutput


class Console:
    SAVE_TITLE = TermCode(f'{CSI}22;0t')
    RESTORE_TITLE = TermCode(f'{CSI}23;0t')

    def __init__(self, encoding=None, allow_title_change=False):
        """
        A class representing a console

        @param encoding             The encoding to use for the console.
                                    Defaults to None.
        @param allow_title_change   If False, do not allow the console
                                    title to be changed. Defaults to False.
        """
        self.initialized = False
        self.output = NULL_OUTPUT

        for stream in (sys.stderr, sys.stdout):
            output = StreamOutput(stream, encoding=encoding)
            if output.use_term_codes:
                self.output = output
                self.initialized = True
                break

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
        """
        Change the title of the console

        Has no effect if there is no known way to set the title.
        Will use either terminal sequences or Windows API.

        @param title    A string to set the console title to.
        """
        if self._title_func is None:
            return

        self._title_func(title)

    def send_code(self, code):
        """
        Send a console code to the console stream

        This has no effect if there is no known console stream
        supporting terminal sequences.

        @param code A string or TermCode to send to the console.
        """
        if not self.initialized:
            return

        self.output.write(code)

    def save_title(self):
        """
        Save the current title on the stack

        This sends a console sequence to save
        the current title on the stack
        """
        if not self.allow_title_change:
            return

        self.send_code(self.SAVE_TITLE)

    def restore_title(self):
        """
        Restore the last title from the stack

        This sends a console sequence to restore
        the last title from the stack
        """
        if not self.allow_title_change:
            return

        self.send_code(self.RESTORE_TITLE)

    def _change_title_term_sequence(self, title):
        self.send_code(f'{CSI}0;{title}{BEL}')

    def _change_title_win_api(self, title):
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW(title)
