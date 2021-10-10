import functools
from threading import Lock
from .utils import supports_terminal_sequences, TERMINAL_SEQUENCES, write_string


class MultilinePrinterBase:
    def __init__(self, stream=None, lines=1):
        self.stream = stream
        self.maximum = lines - 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.end()

    def print_at_line(self, text, pos):
        pass

    def end(self):
        pass

    def _add_line_number(self, text, line):
        if self.maximum:
            return f'{line + 1}: {text}'
        return text

    def write(self, *text):
        write_string(''.join(text), self.stream)


class QuietMultilinePrinter(MultilinePrinterBase):
    pass


class MultilineLogger(MultilinePrinterBase):
    def write(self, *text):
        self.stream.debug(''.join(text))

    def print_at_line(self, text, pos):
        # stream is the logger object, not an actual stream
        self.write(self._add_line_number(text, pos))


class BreaklineStatusPrinter(MultilinePrinterBase):
    def print_at_line(self, text, pos):
        self.write(self._add_line_number(text, pos), '\n')


class MultilinePrinter(MultilinePrinterBase):
    def __init__(self, stream=None, lines=1, preserve_output=True):
        super().__init__(stream, lines)
        self.preserve_output = preserve_output
        self._lastline = self._lastlength = 0
        self._movelock = Lock()
        self._HAVE_FULLCAP = supports_terminal_sequences(self.stream)

    def lock(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with self._movelock:
                return func(self, *args, **kwargs)
        return wrapper

    def _move_cursor(self, dest):
        current = min(self._lastline, self.maximum)
        yield '\r'
        distance = dest - current
        if distance < 0:
            yield TERMINAL_SEQUENCES['UP'] * -distance
        elif distance > 0:
            yield TERMINAL_SEQUENCES['DOWN'] * distance
        self._lastline = dest

    @lock
    def print_at_line(self, text, pos):
        if self._HAVE_FULLCAP:
            self.write(*self._move_cursor(pos), TERMINAL_SEQUENCES['ERASE_LINE'], text)

        text = self._add_line_number(text, pos)
        textlen = len(text)
        if self._lastline == pos:
            # move cursor at the start of progress when writing to same line
            prefix = '\r'
            if self._lastlength > textlen:
                text += ' ' * (self._lastlength - textlen)
            self._lastlength = textlen
        else:
            # otherwise, break the line
            prefix = '\n'
            self._lastlength = textlen
        self.write(prefix, text)
        self._lastline = pos

    @lock
    def end(self):
        # move cursor to the end of the last line, and write line break
        # so that other to_screen calls can precede
        text = self._move_cursor(self.maximum) if self._HAVE_FULLCAP else []
        if self.preserve_output:
            self.write(*text, '\n')
            return

        if self._HAVE_FULLCAP:
            self.write(
                *text, TERMINAL_SEQUENCES['ERASE_LINE'],
                f'{TERMINAL_SEQUENCES["UP"]}{TERMINAL_SEQUENCES["ERASE_LINE"]}' * self.maximum)
        else:
            self.write(*text, ' ' * self._lastlength)
