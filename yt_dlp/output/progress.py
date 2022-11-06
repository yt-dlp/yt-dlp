import enum
import functools
from threading import Lock

from .hoodoo import CSI, Color, TermCode, Typeface
from .logging import NULL_OUTPUT, LogLevel, StreamOutput, default_logger

ERASE_LINE = f'{CSI}K'
MOVE_UP = f'{CSI}A'
MOVE_DOWN = '\n'


def move_cursor(distance):
    return -distance * MOVE_UP if distance < 0 else distance * MOVE_DOWN


def _synchronized(func=None, /):
    if func is None:
        return _synchronized

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        if not hasattr(self, '__lock'):
            self.__lock = Lock()

        with self.__lock:
            return func(self, *args, **kwargs)

    return wrapped


# TODO(logging): Allow passing of progress dict
class Progress:
    class Style(enum.Enum):
        DOWNLOADED_BYTES = TermCode(Color.LIGHT | Color.BLUE)
        PERCENT = TermCode(Color.LIGHT | Color.BLUE)
        ETA = TermCode(Color.YELLOW)
        SPEED = TermCode(Color.GREEN)
        ELAPSED = TermCode(Typeface.BOLD, Color.WHITE)
        TOTAL_BYTES = TermCode()
        TOTAL_BYTES_ESTIMATE = TermCode()

    @classmethod
    def make_progress(cls, logger=default_logger, level=LogLevel.INFO, console=None,
                      *, lines=1, preserve=True, newline=False, disable=False):
        if disable:
            output = NULL_OUTPUT

        else:
            output = logger.mapping.get(level)
            if not isinstance(output, StreamOutput):
                newline = True

        return cls(output, lines=lines, preserve=preserve, newline=newline, console=console)

    def __init__(self, output, lines=1, preserve=True, newline=False, console=None):
        self.output = output
        self.console = console
        self.maximum = lines - 1
        self.preserve = preserve
        self.newline = newline
        self._lastline = 0
        self._lastlength = 0

    @_synchronized
    def print_at_line(self, text, pos: int):
        if not self.output:
            return

        if self.newline:
            self._write(self._add_line_number(text, pos), '\n')
            return

        if self.output.allow_color:
            self._write(self._move_to(pos), ERASE_LINE, text)
            return

        text = self._add_line_number(text, pos)
        textlen = len(text)
        if self._lastline == pos:
            # move cursor at the start of progress when writing to same line
            prefix = '\r'
            if self._lastlength > textlen:
                text += ' ' * (self._lastlength - textlen)
        else:
            # otherwise, break the line
            prefix = '\n'

        self._write(prefix, text)
        self._lastlength = textlen
        self._lastline = pos

    @_synchronized
    def close(self):
        if not self.output or self.newline:
            return

        # move cursor to the end of the last line and write line break
        if self.preserve:
            if self.output.allow_color:
                self._write(self._move_to(self.maximum), '\n')
            else:
                self._write('\n')
            return

        # Try to clear as many lines as possible
        if self.output.allow_color:
            self._write(
                self._move_to(self.maximum), ERASE_LINE,
                f'{MOVE_UP}{ERASE_LINE}' * self.maximum)
        else:
            self._write('\r', ' ' * self._lastlength, '\r')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _write(self, *text):
        self.output.log(''.join(text))

    def _add_line_number(self, text, line):
        if self.maximum:
            return f'{line + 1}: {text}'
        return text

    def _move_to(self, line):
        distance = line - self._lastline
        self._lastline = line
        return f'\r{move_cursor(distance)}'
