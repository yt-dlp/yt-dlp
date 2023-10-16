import functools
from threading import Lock

from .utils import supports_terminal_sequences, write_string

CONTROL_SEQUENCES = {
    'DOWN': '\n',
    'UP': '\033[A',
    'ERASE_LINE': '\033[K',
    'RESET': '\033[0m',
}


_COLORS = {
    'BLACK': '0',
    'RED': '1',
    'GREEN': '2',
    'YELLOW': '3',
    'BLUE': '4',
    'PURPLE': '5',
    'CYAN': '6',
    'WHITE': '7',
}


_TEXT_STYLES = {
    'NORMAL': '0',
    'BOLD': '1',
    'UNDERLINED': '4',
}


def format_text(text, f):
    '''
    @param f    String representation of formatting to apply in the form:
                [style] [light] font_color [on [light] bg_color]
                E.g. "red", "bold green on light blue"
    '''
    f = f.upper()
    tokens = f.strip().split()

    bg_color = ''
    if 'ON' in tokens:
        if tokens[-1] == 'ON':
            raise SyntaxError(f'Empty background format specified in {f!r}')
        if tokens[-1] not in _COLORS:
            raise SyntaxError(f'{tokens[-1]} in {f!r} must be a color')
        bg_color = f'4{_COLORS[tokens.pop()]}'
        if tokens[-1] == 'LIGHT':
            bg_color = f'0;10{bg_color[1:]}'
            tokens.pop()
        if tokens[-1] != 'ON':
            raise SyntaxError(f'Invalid format {f.split(" ON ", 1)[1]!r} in {f!r}')
        bg_color = f'\033[{bg_color}m'
        tokens.pop()

    if not tokens:
        fg_color = ''
    elif tokens[-1] not in _COLORS:
        raise SyntaxError(f'{tokens[-1]} in {f!r} must be a color')
    else:
        fg_color = f'3{_COLORS[tokens.pop()]}'
        if tokens and tokens[-1] == 'LIGHT':
            fg_color = f'9{fg_color[1:]}'
            tokens.pop()
        fg_style = tokens.pop() if tokens and tokens[-1] in _TEXT_STYLES else 'NORMAL'
        fg_color = f'\033[{_TEXT_STYLES[fg_style]};{fg_color}m'
        if tokens:
            raise SyntaxError(f'Invalid format {" ".join(tokens)!r} in {f!r}')

    if fg_color or bg_color:
        text = text.replace(CONTROL_SEQUENCES['RESET'], f'{fg_color}{bg_color}')
        return f'{fg_color}{bg_color}{text}{CONTROL_SEQUENCES["RESET"]}'
    else:
        return text


class MultilinePrinterBase:
    def __init__(self, stream=None, lines=1):
        self.stream = stream
        self.maximum = lines - 1
        self._HAVE_FULLCAP = supports_terminal_sequences(stream)

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
            yield CONTROL_SEQUENCES['UP'] * -distance
        elif distance > 0:
            yield CONTROL_SEQUENCES['DOWN'] * distance
        self._lastline = dest

    @lock
    def print_at_line(self, text, pos):
        if self._HAVE_FULLCAP:
            self.write(*self._move_cursor(pos), CONTROL_SEQUENCES['ERASE_LINE'], text)
            return

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
                *text, CONTROL_SEQUENCES['ERASE_LINE'],
                f'{CONTROL_SEQUENCES["UP"]}{CONTROL_SEQUENCES["ERASE_LINE"]}' * self.maximum)
        else:
            self.write('\r', ' ' * self._lastlength, '\r')
