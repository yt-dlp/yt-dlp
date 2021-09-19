import re

from threading import Lock

try:
    # curses is in standard modules, just like sqlite in cookies.py,
    # it is not present under some circumstances (especially when running on Windows)
    import curses
    has_curses = True
except ImportError:
    has_curses = False


class MultilinePrinterBase():
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.end()

    def print_at_line(self, text, pos):
        pass

    def end(self):
        pass


class MultilinePrinter(MultilinePrinterBase):

    def __init__(self, stream, lines):
        """
        @param stream stream to write to
        @lines number of lines to be written
        """
        self.stream = stream
        try:
            # calling this multiple times won't throw errors and safe
            curses.setupterm()
            self.UP = self.tputs('cuu1') or self.tputs('up')
            self.DOWN = self.tputs('cud1') or self.tputs('do')
            self.ERASE_LINE = self.tputs('el') or self.tputs('ce')
            self.CARRIAGE_RETURN = self.tputs('cr') or '\r'
            self._HAVE_FULLCAP = self._isatty() and self.UP and self.DOWN and self.ERASE_LINE
        except curses.error:
            self.UP = self.DOWN = self.ERASE_LINE = None
            self.CARRIAGE_RETURN = '\r'
            self._HAVE_FULLCAP = False

        # lines are numbered from top to bottom, counting from 0 to self.maximum
        self.maximum = lines - 1
        self.lastline = 0
        self.lastlength = 0

        self.movelock = Lock()

    @property
    def have_fullcap(self):
        """
            True if the TTY is allowing to control cursor,
            allowing it to show multiline progress
        """
        return self._HAVE_FULLCAP

    def _isatty(self):
        try:
            return self.stream.isatty()
        except BaseException:
            return False

    def tputs(self, cap_name):
        cap = curses.tigetstr(cap_name)
        if not cap:
            return None
        # needed to strip delays
        return re.sub(rb'\$<\d+>[/*]?', '', cap).decode()

    def _move_cursor(self, dest):
        current = min(self.lastline, self.maximum)
        self.stream.write(self.CARRIAGE_RETURN)
        if current == dest:
            # current and dest are at same position, no need to move cursor
            return
        elif current > dest:
            # when maximum == 2,
            # 0. dest
            # 1. 
            # 2. current
            self.stream.write(self.UP * (current - dest))
        elif current < dest:
            # when maximum == 2,
            # 0. current
            # 1. 
            # 2. dest
            self.stream.write(self.DOWN * (dest - current))
        self.lastline = dest

    def print_at_line(self, text, pos):
        with self.movelock:
            if self.have_fullcap:
                self._move_cursor(pos)
                self.stream.write(self.ERASE_LINE)
                self.stream.write(text)
            else:
                if self.maximum != 0:
                    # let user know about which line is updating the status
                    text = f'{pos + 1}: ${text}'
                textlen = len(text)
                if self.lastline == pos:
                    # move cursor at the start of progress when writing to same line
                    self.stream.write(self.CARRIAGE_RETURN)
                    if self.lastlength > textlen:
                        text += ' ' * (self.lastlength - textlen)
                    self.lastlength = textlen
                else:
                    # otherwise, break the line
                    self.stream.write('\n')
                    self.lastlength = 0
                self.stream.write(text)
                self.lastline = pos

    def end(self):
        # move cursor to the end of the last line, and write line break
        # so that other to_screen calls can precede
        self._move_cursor(self.maximum)
        self.stream.write('\n')


class QuietMultilinePrinter(MultilinePrinterBase):
    def __init__(self):
        self.have_fullcap = True


class BreaklineStatusPrinter(MultilinePrinterBase):

    def __init__(self, stream, lines):
        """
        @param stream stream to write to
        """
        self.stream = stream
        self.maximum = lines
        self.have_fullcap = True

    def print_at_line(self, text, pos):
        if self.maximum != 0:
            # let user know about which line is updating the status
            text = f'{pos + 1}: ${text}'
        self.stream.write(text + '\n')
