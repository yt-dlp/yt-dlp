import functools
from threading import Lock

from .hoodoo import CSI
from .logging import NULL_OUTPUT, LogLevel, StreamOutput, default_logger
from .progress_formatting import apply_progress_format

ERASE_LINE = f'{CSI}K'
MOVE_UP = f'{CSI}A'
MOVE_DOWN = '\n'


def move_cursor(distance):
    return -distance * MOVE_UP if distance < 0 else distance * MOVE_DOWN


def _synchronized(func=None):
    if func is None:
        return _synchronized

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        if not hasattr(self, '__lock'):
            self.__lock = Lock()

        with self.__lock:
            return func(self, *args, **kwargs)

    return wrapped


class Progress:
    @classmethod
    def make_progress(cls, logger=default_logger, level=LogLevel.INFO,
                      *, lines=1, preserve=True, newline=False, disable=False):
        if disable:
            output = NULL_OUTPUT

        else:
            output = logger.mapping.get(level)
            if not isinstance(output, StreamOutput):
                newline = True

        return cls(output, lines=lines, preserve=preserve, newline=newline)

    def __init__(self, output, lines=1, preserve=True, newline=False):
        self.output = output
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

        if self.output.use_color:
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
            if self.output.use_color:
                self._write(self._move_to(self.maximum), '\n')
            else:
                self._write('\n')
            return

        # Try to clear as many lines as possible
        if self.output.use_color:
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


class ProgressReporter:
    def __init__(self, ydl, prefix, *, lines=1, newline=False, preserve=False, disabled=False, templates={}):
        # XXX(output): This fails if ydl fake without console or logger gets passed
        self._ydl = ydl
        self._progress = Progress.make_progress(ydl.logger, lines=lines, preserve=preserve, newline=newline)
        self.disabled = disabled
        # Pass in a `progress_template` (`params.get('progress_template', {})`)
        # XXX(output): This allows `{prefix}`, `{prefix}-title` and `{prefix}-finish` for all prefixes
        self._screen_template = templates.get(prefix) or f'[{prefix}] %(progress._default_template)s'
        self._title_template = templates.get(f'{prefix}-title') or 'yt-dlp %(progress._default_template)s'
        self._finish_template = templates.get(f'{prefix}-finish') or f'[{prefix}] {prefix.capitalize()} completed'

    def report_progress(self, progress_dict):
        line = progress_dict.get('progress_idx') or 0
        if self.disabled:
            if progress_dict['status'] == 'finished':
                self._progress.print_at_line(self._finish_template, line)

            return

        apply_progress_format(progress_dict, self._progress.output.use_color)

        progress_data = progress_dict.copy()
        progress_data = {
            'info': progress_data.pop('info_dict'),
            'progress': progress_data,
        }

        self._progress.print_at_line(self._ydl.evaluate_outtmpl(
            self._screen_template, progress_data), line)

        if self._ydl.console.allow_title_change:
            self._ydl.console.change_title(self._ydl.evaluate_outtmpl(
                self._title_template, progress_data))

    def close(self):
        self._progress.close()
