import re
from collections import defaultdict
from threading import Lock

from .hoodoo import CSI, ERASE_LINE, format_text, move_cursor
from .logging_output import logger as _logging_logger
from ..compat import compat_os_name
from ..utils import preferredencoding, supports_terminal_sequences


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

    def encode(self, text, fallback, encoding=None):
        """
        Try to encode text for this output with the specified encoding

        If the initial round trip failed, use the fallback text instead.

        @param text         The text to try and encode.
        @param fallback     The fallback text to use if encoding failed.
        @param encoding     The encoding to use for the process.
                            If None, take the preferred encoding from the specified output.
        """
        return text

    def write(self, string):
        """
        Write a string to the output

        This method MUST be overridden by a subclass.

        This function exists to write a specific string to the output unchanged.
        Use the `log` message to write to the output in a managed way.

        @param string   The string to write to the output.
        """
        raise NotImplementedError(f'`{type(self).__name__}.write` must be overridden')

    def log(self, message):
        """
        Log a message to the output

        @param message  The message to log to the output.
        @param error    Either a bool, indicating if error information should be added
                        or a str, which will be added as the error information to the message.
        """
        self.write(message.rstrip())

    def status(self, status_id, line, message):
        """
        Send a status update to the output

        `register_status` MUST be called before calling the
        `status` function with that specific `status_id`.

        @param status_id    The id for the status to write to.
        @param line         The line index to write to.
                            Must be smaller than the registered line count.
        @param message      The content to write to the status line.
                            It MUST NOT contain newlines besides
                            an optional trailing one.
        """
        self.write(message.rstrip())

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
        self.lock = Lock()

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
    _CONHOST_WORKAROUND_RE = re.compile('([\r\n]+)')

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
        self._buffer = stream

        try:
            stream.flush()
            self._flush = stream.flush
        except Exception:
            self._flush = None

        # stream.encoding can be None. See https://github.com/yt-dlp/yt-dlp/issues/2711
        self._encoding = encoding or getattr(stream, 'encoding', None)
        self._strict_encoding = self._encoding or 'ascii'

        if 'b' in getattr(stream, 'mode', ''):
            self._encoding = self._encoding or preferredencoding()
        elif hasattr(stream, 'buffer'):
            self._encoding = self._encoding or preferredencoding()
            self._buffer = stream.buffer

        try:
            self._isatty = bool(stream.isatty())
        except Exception:
            self._isatty = False

        supports_term_codes = supports_terminal_sequences(stream)
        self._use_term_codes = supports_term_codes if use_term_codes is None else use_term_codes
        self._use_conhost_workaround = compat_os_name == 'nt' and supports_term_codes

        if group_id is None:
            group_id = 0 if self.isatty else _StreamOutputGroup.next_id()
        self._output_group = self._OUTPUT_GROUPS[group_id]

        if self.use_term_codes:
            self._output_group.using_term_codes = True

    @property
    def isatty(self):
        return self._isatty

    @property
    def encoding(self):
        return self._encoding

    def encode(self, text, fallback, encoding=None):
        encoding = encoding or self._strict_encoding
        round_trip = text.encode(encoding, 'ignore').decode(encoding)

        return text if round_trip == text else fallback

    def write(self, string):
        """
        Write a string to the output

        This function exists to write a specific string to the output unchanged.
        Use the `log` message to write to the output in a managed way.

        @param string   The string to write to the output.
        """
        with self._output_group.lock:
            self._write(string)

    def _write(self, string):
        assert isinstance(string, str)
        if not self._buffer:
            return

        if self._use_conhost_workaround:
            # Workaround for conhost breaking up newlines incorrectly
            string = self._apply_conhost_workaround(string)

        if self._encoding:
            string = string.encode(self._encoding, 'ignore')

        self._buffer.write(string)
        if self._flush:
            self._flush()

    def log(self, message):
        with self._output_group.lock:
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

            self._write(message)
            if self._output_group.using_term_codes:
                self._output_group.reset_last_status()

            self._output_group.current_position = 0 if message.endswith('\n') else -1

    def status(self, status_id, line, message):
        with self._output_group.lock:
            if self._output_group.using_term_codes:
                self._write(f'{self._move_to(status_id, line)}\r{ERASE_LINE}{message}')
                if message.endswith('\n'):
                    self._output_group.current_position += 1
                return

            message_length = len(message)
            previous_length = self._output_group.get_previous_length(status_id, line)
            if previous_length is not None:
                pad = ' ' * (previous_length - len(message))
                message = f'\r{message}{pad}'

            elif self._output_group.current_position == -1:
                message = f'\n{message}'

            self._write(message)
            self._output_group.set_last_status(status_id, line, message_length)
            self._output_group.current_position = 0 if message.endswith('\n') else -1

    def register_status(self, lines=1):
        """
        Register status lines with the output

        @param lines    The amount of lines this status occupies.
                        Defaults to 1.
        @returns        The integer `status_id` for that status.
        """
        if not self.use_term_codes:
            return

        with self._output_group.lock:
            status_id = self._output_group.next_status_id()
            self._output_group.status_sizes[status_id] = lines
            return status_id

    def unregister_status(self, status_id):
        """
        Unregister status lines with the output

        After unregistering that `status_id`,
        the `status` or `unregister_status` functions
        MUST NOT be called with that specific `status_id` again.

        The status lines will be removed from the status section.

        @param status_id    The id for the status to unregister.
        """
        with self._output_group.lock:
            if not self.use_term_codes:
                self._output_group.reset_last_status()
                return

            self._write(f'{self._move_to(status_id, 0)}{CSI}{self._output_group.status_sizes[status_id]}M')
            del self._output_group.status_sizes[status_id]

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

    @classmethod
    def _apply_conhost_workaround(cls, message):
        return cls._CONHOST_WORKAROUND_RE.sub(r' \1', message)


class ClassOutput(OutputBase):
    """An output for writing to class functions"""
    def __init__(self, func):
        self._logging_function = func

    def write(self, string):
        """
        Write a string to the output

        This function exists to write a specific string to the output unchanged.
        Use the `log` message to write to the output in a managed way.

        @param string   The string to write to the output.
        """
        self._logging_function(string)


class LoggingOutput(OutputBase):
    """An output for writing to the logging module"""
    REMOVABLE_PREFIXES = {'[debug] ', 'ERROR: ', 'WARNING: '}

    def __init__(self, level):
        self.level = level

    def write(self, string):
        """
        Write a string to the output

        This function exists to write a specific string to the output unchanged.
        Use the `log` message to write to the output in a managed way.

        @param string   The string to write to the output.
        """
        for prefix in self.REMOVABLE_PREFIXES:
            if string.startswith(prefix):
                string = string[len(prefix):]
        if string.startswith('['):
            string = string.partition(']')[2].lstrip()
        _logging_logger.log(self.level, string)


class NullOutput(OutputBase):
    """A dummy output having no effect"""
    def write(self, string):
        """Does nothing"""
        pass

    def log(self, message):
        """Does nothing"""
        pass

    def status(self, status_id, line, message):
        """Does nothing"""
        pass

    def __bool__(self):
        return False


NULL_OUTPUT = NullOutput()
