import copy
import inspect
import logging
import os
import shutil
import subprocess
import sys
import traceback
import warnings
from enum import Enum

from .hoodoo import Color, TermCode
from .outputs import NULL_OUTPUT, ClassOutput, LoggingOutput, StreamOutput
from ..compat import functools
from ..utils import deprecation_warning, variadic


class LogLevel(Enum):
    SCREEN = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


class Verbosity(Enum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2


class Style:
    HEADER = TermCode.make(Color.YELLOW)
    EMPHASIS = TermCode.make(Color.LIGHT | Color.BLUE)
    FILENAME = TermCode.make(Color.GREEN)
    ID = TermCode.make(Color.GREEN)
    DELIM = TermCode.make(Color.BLUE)
    ERROR = TermCode.make(Color.RED)
    WARNING = TermCode.make(Color.YELLOW)
    SUPPRESS = TermCode.make(Color.LIGHT | Color.BLACK)


def redirect_warnings(logger):
    """ Redirect messages from the `warnings` module to a `Logger` """
    _old_showwarning = warnings.showwarning

    def _warnings_showwarning(message, category, filename, lineno, file=None, line=None):
        if file is not None:
            _old_showwarning(message, category, filename, lineno, file, line)
            return

        module = inspect.getmodule(None, filename)
        if module:
            filename = module.__name__
        logger.warning(f'{category.__name__}: {message} ({filename}:{lineno})')

    warnings.showwarning = _warnings_showwarning


class Logger:
    """
    A YoutubeDL output/logging facility

    After instancing all `LogLevel`s beside `LogLevel.SCREEN` are NULL_OUTPUT.
    To initialize them to the appropriate values one SHOULD call one of:
    - `setup_stream_logger`
    - `setup_class_logger`
    - `setup_logging_logger`
    Alternatively you can also define your own outputs deriving `OutputBase`
    and set those for the LogLevel in the mapping of the logger.
    You are free to call any of the setup functions more than once.

    Output instances might be shared between `LogLevel`s.

    To enable the bidirectional workaround, call `init_bidi_workaround()`.
    """

    def __init__(self, screen, verbosity=Verbosity.NORMAL,
                 *, encoding=None, use_term_codes=None, disable_progress=False):
        self._bidi_initalized = False
        self._pref_encoding = encoding
        self._use_term_codes = use_term_codes
        self._verbosity = verbosity
        self.message_cache = set()
        self.disable_progress = disable_progress

        screen_output = NULL_OUTPUT if screen is None else StreamOutput(screen, use_term_codes, encoding)
        self.mapping = {
            LogLevel.SCREEN: screen_output,
            LogLevel.DEBUG: NULL_OUTPUT,
            LogLevel.INFO: NULL_OUTPUT,
            LogLevel.ERROR: NULL_OUTPUT,
            LogLevel.WARNING: NULL_OUTPUT,
        }

    def make_derived(self, **overrides):
        derived = copy.copy(self)
        for name, wrapper in overrides.items():
            base = getattr(derived, name, None)
            if base is None:
                raise NameError(f"No method {name!r} exists for type {type(derived).__name__}")

            wrapped = functools.update_wrapper(wrapper(base), base)
            setattr(derived, name, wrapped)

        derived.mapping = self.mapping.copy()
        return derived

    def setup_stream_logger(self, stdout, stderr, *, no_warnings=False):
        stdout_output = NULL_OUTPUT if stdout is None else StreamOutput(stdout, self._use_term_codes, self._pref_encoding)
        stderr_output = NULL_OUTPUT if stderr is None else StreamOutput(stderr, self._use_term_codes, self._pref_encoding)

        self.mapping.update({
            LogLevel.DEBUG: (
                stderr_output if self._verbosity is Verbosity.VERBOSE
                else NULL_OUTPUT),
            LogLevel.INFO: stdout_output,
            LogLevel.WARNING: NULL_OUTPUT if no_warnings else stderr_output,
            LogLevel.ERROR: stderr_output,
        })
        return self

    def setup_class_logger(self, logger):
        debug_output = ClassOutput(logger.debug)
        warning_output = ClassOutput(logger.warning)
        error_output = ClassOutput(logger.error)

        self.mapping.update({
            LogLevel.DEBUG: debug_output,
            LogLevel.INFO: debug_output,
            LogLevel.WARNING: warning_output,
            LogLevel.ERROR: error_output,
        })
        return self

    def setup_logging_logger(self):
        self.mapping.update({
            LogLevel.DEBUG: LoggingOutput(logging.DEBUG),
            LogLevel.INFO: LoggingOutput(logging.INFO),
            LogLevel.WARNING: LoggingOutput(logging.WARNING),
            LogLevel.ERROR: LoggingOutput(logging.ERROR),
        })
        return self

    def log(self, level, message, *, newline=True, once=False, suppress=False, trace=None, prefix=None):
        output = self.mapping.get(level)
        if not output or suppress:
            return

        assert isinstance(message, str)

        if once:
            if message in self.message_cache:
                return
            self.message_cache.add(message)

        if self._bidi_initalized and output.ALLOW_BIDI:
            message = self._apply_bidi_workaround(message)

        if prefix:
            message = ' '.join((*map(str, variadic(prefix)), message))

        if level is LogLevel.ERROR and self._verbosity is Verbosity.VERBOSE:
            message += '\n'
            if trace is not None:
                message += str(trace)

            elif sys.exc_info()[0]:  # called from an except block
                message += traceback.format_exc()

            else:
                message += ''.join(traceback.format_list(traceback.extract_stack()))

        if newline:
            message += '\n'

        output.log(message)

    def format(self, level, text, *text_formats):
        logger = self.mapping.get(level)
        if not logger:
            return text

        return logger.format(str(text), *text_formats)

    def try_encoding(self, level, text, fallback_text, pref_encoding=None):
        logger = self.mapping.get(level)
        if not isinstance(logger, StreamOutput):
            return text

        # stream.encoding can be None. See https://github.com/yt-dlp/yt-dlp/issues/2711
        encoding = pref_encoding or getattr(logger._stream, 'encoding', None) or 'ascii'
        round_trip = text.encode(encoding, 'ignore').decode(encoding)

        return text if round_trip == text else fallback_text

    def screen(self, message, newline=True):
        """Print message to screen"""
        self.log(LogLevel.SCREEN, message, newline=newline)

    def debug(self, message, once=False):
        """Print debug message to stderr"""
        self.log(LogLevel.DEBUG, message, once=once)

    def info(self, message, newline=True, quiet=None, once=False):
        """Print message to stdout"""
        suppress = (
            False if self._verbosity is Verbosity.VERBOSE
            else quiet if quiet is not None
            else self._verbosity is Verbosity.QUIET)

        self.log(LogLevel.INFO, message, suppress=suppress, newline=newline, once=once)

    def warning(self, message, once=False):
        """
        Print a message to stderr, prefixed with 'WARNING:'
        If stderr is a tty file the prefix will be colored
        """
        self.log(LogLevel.WARNING, message, once=once,
                 prefix=self.format(LogLevel.WARNING, "WARNING:", Style.WARNING))

    def deprecation_warning(self, message, *, stacklevel=0):
        deprecation_warning(
            message, stacklevel=stacklevel + 1, printer=self.handle_error,
            is_error=False, prefix=True)

    def deprecated_feature(self, message):
        self.log(LogLevel.WARNING, message, once=True,
                 prefix=self.format(LogLevel.WARNING, "Deprecated Feature:", Style.ERROR))

    def error(self, message, once=False):
        """Print message to stderr"""
        self.log(LogLevel.ERROR, message, once=once)

    def handle_error(self, message, trace=None, is_error=True, prefix=True):
        """
        Determine action to take when a download problem appears.
        Optionally prefix the message with 'ERROR:'.
        If stderr is a tty the prefix will be colored.

        @param trace       If given, is additional traceback information
        @param is_error    Useful only in a derived logger
        """
        if prefix:
            prefix = self.format(LogLevel.ERROR, "ERROR:", Style.ERROR)

        self.log(LogLevel.ERROR, message, trace=trace, prefix=prefix)

    def init_bidi_workaround(self):
        """
        Initialize the bidirectional workaround

        It raises `ImportError` systems not providing the `pty` module.
        This is notably the case on Windows machines.
        It also requires either `bidiv` or `fribidi` to be accessible.

        The width of the terminal will be collected once at startup only.
        If you need to update the terminal width passed to the executable
        call `init_bidi_workaround` after the resize, which will spawn a new
        bidi executable with the updated width.
        """
        import pty

        if self._bidi_initalized:
            self._bidi_reader.close()
            self._bidi_process.terminate()

        master, slave = pty.openpty()
        width = shutil.get_terminal_size().columns
        width_args = [] if width is None else ['-w', str(width)]
        sp_kwargs = {'stdin': subprocess.PIPE, 'stdout': slave, 'stderr': sys.stderr}
        try:
            _output_process = subprocess.Popen(['bidiv'] + width_args, **sp_kwargs)
        except OSError:
            _output_process = subprocess.Popen(['fribidi', '-c', 'UTF-8'] + width_args, **sp_kwargs)

        self._bidi_process = _output_process
        assert _output_process.stdin is not None
        self._bidi_writer = _output_process.stdin
        self._bidi_reader = os.fdopen(master, 'rb')
        self._bidi_initalized = True

    def _apply_bidi_workaround(self, message):
        # `init_bidi_workaround()` MUST have been called prior.
        line_count = message.count('\n') + 1

        self._bidi_writer.write(f'{message}\n')
        self._bidi_writer.flush()
        result = b''.join(self._bidi_reader.readlines(line_count)).decode()
        return result[:-1]


default_logger = Logger(None, Verbosity.QUIET).setup_stream_logger(None, sys.stderr)
