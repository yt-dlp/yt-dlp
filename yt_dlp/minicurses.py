from threading import Lock
from .utils import supports_terminal_sequences, TERMINAL_SEQUENCES


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


class QuietMultilinePrinter(MultilinePrinterBase):
    pass


class MultilineLogger(MultilinePrinterBase):
    def print_at_line(self, text, pos):
        # stream is the logger object, not an actual stream
        self.stream.debug(self._add_line_number(text, pos))


class BreaklineStatusPrinter(MultilinePrinterBase):
    def print_at_line(self, text, pos):
        self.stream.write(self._add_line_number(text, pos) + '\n')


class MultilinePrinter(MultilinePrinterBase):
    def __init__(self, stream=None, lines=1, preserve_output=True):
        super().__init__(stream, lines)
        self.preserve_output = preserve_output
        self._lastline = self._lastlength = 0
        self._movelock = Lock()
        self._HAVE_FULLCAP = supports_terminal_sequences(self.stream)

    def lock(func):
        def wrapper(self, *args, **kwargs):
            with self._movelock:
                return func(self, *args, **kwargs)
        return wrapper

    def _move_cursor(self, dest):
        current = min(self._lastline, self.maximum)
        self.stream.write('\r')
        distance = dest - current
        if distance < 0:
            self.stream.write(TERMINAL_SEQUENCES['UP'] * -distance)
        elif distance > 0:
            self.stream.write(TERMINAL_SEQUENCES['DOWN'] * distance)
        self._lastline = dest

    @lock
    def print_at_line(self, text, pos):
        if self._HAVE_FULLCAP:
            self._move_cursor(pos)
            self.stream.write(TERMINAL_SEQUENCES['ERASE_LINE'])
            self.stream.write(text)
            return

        text = self._add_line_number(text, pos)
        textlen = len(text)
        if self._lastline == pos:
            # move cursor at the start of progress when writing to same line
            self.stream.write('\r')
            if self._lastlength > textlen:
                text += ' ' * (self._lastlength - textlen)
            self._lastlength = textlen
        else:
            # otherwise, break the line
            self.stream.write('\n')
            self._lastlength = textlen
        self.stream.write(text)
        self._lastline = pos

    @lock
    def end(self):
        # move cursor to the end of the last line, and write line break
        # so that other to_screen calls can precede
        if self._HAVE_FULLCAP:
            self._move_cursor(self.maximum)
        if self.preserve_output:
            self.stream.write('\n')
            return

        if self._HAVE_FULLCAP:
            self.stream.write(
                TERMINAL_SEQUENCES['ERASE_LINE']
                + f'{TERMINAL_SEQUENCES["UP"]}{TERMINAL_SEQUENCES["ERASE_LINE"]}' * self.maximum)
        else:
            self.stream.write(' ' * self._lastlength)
