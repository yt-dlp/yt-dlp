from collections import defaultdict
from threading import Lock

from .hoodoo import CSI, ERASE_LINE, format_text, move_cursor
from .logging_output import logger as _logging_logger
from ..compat import functools
from ..utils import supports_terminal_sequences, write_string


class OutputBase:
    """
    The base for every output

    Each output will always have the following attributes:
    @param ALLOW_BIDI       Allow the use of the bidi workaround
                            for the specified output.
    @param use_term_codes   Use terminal codes for the output.
    """
    ALLOW_BIDI = False
    _use_term_codes = False

    @property
    def use_term_codes(self):
        return self._use_term_codes

    def format(self, text, *text_formats):
        """
        Format text using specified text formats

        @param text             The text to format. It will be wrapped in the
                                color start and end sequences.
        @params text_formats    A TermCode, Color or Typeface.

        @returns                The text with the requested formatting if supported.
        """
        if not self.use_term_codes:
            return text

        return format_text(text, *text_formats)

    @classmethod
    def _log(cls, message):
        raise NotImplementedError(
            f'At least `{cls.__name__}._log` or both `{cls.__name__}.log` '
            + f'and `{cls.__name__}.status` must be implemented in subclass')

    def log(self, message):
        """Log a message to the output"""
        self._log(message.rstrip())

    def status(self, status_id, line, message):
        """
        Send a status update to the output

        `register_status` MUST be called before calling the
        `status` function with that specific `status_id`.

        @param status_id    The id for the status to write to.
        @param line         The line index to write to.
                            Must be smaller than the registered line count.
        @param message      The content to write to the status line.
                            It SHOULD NOT contain newlines besides
                            an optional trailing one.
        """
        self._log(message.rstrip())

    def register_status(self, lines=1):
        """
        Register status lines with the output

        Does nothing for this output and always returns `0`.

        @param lines    The amount of lines this status output occupies.
                        Defaults to 1.
        @returns        The integer `status_id` for that status.
        """
        return 0

    def unregister_status(self, status_id):
        """
        Unregister status lines with the output

        After unregistering that `status_id`,
        the `status` or `unregister_status` functions
        MUST NOT be called with that specific `status_id` again.

        Does nothing for this output.

        @param status_id    The id for the status to unregister.
        """
        pass


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


class _StreamOutputGroup:
    _CURRENT_ID = 0
    _CURRENT_STATUS_ID = 0

    @classmethod
    def next_id(cls):
        cls._CURRENT_ID -= 1
        return cls._CURRENT_ID

    def next_status_id(self):
        self._CURRENT_STATUS_ID += 1
        return self._CURRENT_STATUS_ID

    def __init__(self):
        self.current_position: int = 0
        self.status_sizes: dict[int, int] = {}
        self.using_term_codes = False

        self._last_status_id: int | None = None
        self._last_line: int | None = None
        self._last_length: int = 0

    def get_previous_length(self, status_id, line):
        if status_id == self._last_status_id and line == self._last_line:
            return self._last_length
        return None

    def set_last_status(self, status_id, line, length):
        self._last_status_id = status_id
        self._last_line = line
        self._last_length = length

    def reset_last_status(self):
        self._last_status_id = None
        self._last_line = None
        self._last_length = 0


class StreamOutput(OutputBase):
    """A managed output for writing to a stream"""
    ALLOW_BIDI = True
    _OUTPUT_GROUPS = defaultdict(_StreamOutputGroup)

    def __init__(self, stream, use_term_codes=None, encoding=None, group_id=None):
        """
        @param stream           A writable stream to write the output to.
        @param use_term_codes   If `True`, use terminal sequences for formatting.
                                If `None`, automatically determine support using
                                `supports_terminal_sequences`. Defaults to `None`.
        @param encoding         The encoding to use when writing to the stream.
                                If `None`, try to guess encoding from global encoding.
                                Defaults to `None`.
        @param group_id         An integer id used to identify an output.
                                Each stream writing to the same output (eg. stdout/stderr, ...)
                                should have the same id. If `None`, try to guess by using `isatty()`.
                                If its result is `True`, the assigned group id will be `0`.
                                Negative values are reserved. Defaults to `None`.
        """
        self._stream = stream
        self._encoding = encoding
        self._use_term_codes = supports_terminal_sequences(stream) if use_term_codes is None else use_term_codes

        if group_id is None:
            group_id = 0 if self.isatty else _StreamOutputGroup.next_id()
        self._output_group = self._OUTPUT_GROUPS[group_id]

        if self.use_term_codes:
            self._output_group.using_term_codes = True

    @functools.cached_property
    def isatty(self):
        try:
            return bool(self._stream.isatty())
        except Exception:
            return False

    @functools.cached_property
    def encoding(self):
        # stream.encoding can be None. See https://github.com/yt-dlp/yt-dlp/issues/2711
        return self._encoding or getattr(self._stream, 'encoding', None) or 'ascii'

    @_synchronized
    def log(self, message: str):
        if self._output_group.status_sizes and self._output_group.using_term_codes:
            lines = message.count('\n')
            if not message.endswith('\n'):
                lines += 1

            message = ''.join((
                self._move_to(None, lines - 1),
                move_cursor(-self._output_group.current_position),
                f'{CSI}{lines}L{message}'))

        elif self._output_group.current_position == -1:
            message = f'\n{message}'

        self._log(message)
        if self._output_group.using_term_codes:
            self._output_group.reset_last_status()

        self._output_group.current_position = 0 if message.endswith('\n') else -1

    @_synchronized
    def status(self, status_id, line, message):
        if not self.use_term_codes:
            message_length = len(message)
            previous_length = self._output_group.get_previous_length(status_id, line)
            if previous_length is not None:
                pad = ' ' * (previous_length - len(message))
                message = f'\r{message}{pad}'

            elif self._output_group.current_position == -1:
                message = f'\n{message}'

            self._log(message)
            self._output_group.set_last_status(status_id, line, message_length)
            self._output_group.current_position = 0 if message.endswith('\n') else -1
            return

        # XXX: This fails for non trailing newlines
        self._log(f'{self._move_to(status_id, line)}\r{ERASE_LINE}{message}')
        if message.endswith('\n'):
            self._output_group.current_position += 1

    @_synchronized
    def register_status(self, lines=1):
        """
        Register status lines with the output

        @param lines    The amount of lines this status occupies.
                        Defaults to 1.
        @returns        The integer `status_id` for that status.
        """
        if not self.use_term_codes:
            return

        status_id = self._output_group.next_status_id()
        self._output_group.status_sizes[status_id] = lines
        return status_id

    @_synchronized
    def unregister_status(self, status_id):
        """
        Unregister status lines with the output

        After unregistering that `status_id`,
        the `status` or `unregister_status` functions
        MUST NOT be called with that specific `status_id` again.

        The status lines will be removed from the status section.

        @param status_id    The id for the status to unregister.
        """
        if not self.use_term_codes:
            self._output_group.reset_last_status()
            return

        self._log(f'{self._move_to(status_id, 0)}{CSI}{self._output_group.status_sizes[status_id]}M')
        del self._output_group.status_sizes[status_id]

    def _log(self, message):
        write_string(message, self._stream, self._encoding)

    def _move_to(self, status_id, position):
        absolute_position = 0
        for other_id, size in self._output_group.status_sizes.items():
            if other_id == status_id:
                break

            absolute_position += size

        desired_position = absolute_position + position
        result = move_cursor(desired_position - self._output_group.current_position)
        self._output_group.current_position = desired_position

        return result


class ClassOutput(OutputBase):
    """An output for writing to class functions"""
    def __init__(self, func):
        self._logging_function = func

    def _log(self, message):
        self._logging_function(message)


class LoggingOutput(OutputBase):
    """An output for writing to the logging module"""
    REMOVABLE_PREFIXES = {'[debug] ', 'ERROR: ', 'WARNING: '}

    def __init__(self, level):
        self.level = level

    def _log(self, message):
        for prefix in self.REMOVABLE_PREFIXES:
            if message.startswith(prefix):
                message = message[len(prefix):]
        if message.startswith('['):
            message = message.partition(']')[2].lstrip()
        _logging_logger.log(self.level, message)


class NullOutput(OutputBase):
    """A dummy output having no effect"""
    def log(self, message):
        pass

    def status(self, status_id, line, message):
        pass

    def __bool__(self):
        return False


NULL_OUTPUT = NullOutput()
