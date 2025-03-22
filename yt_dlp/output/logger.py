import os
import sys
import traceback

from ..minicurses import format_text
from ..utils import (
    Namespace,
    deprecation_warning,
    encode_compat_str,
    supports_terminal_sequences,
    windows_enable_vt_mode,
    write_string,
)
from ..utils.traversal import traverse_obj

_Styles = Namespace(
    HEADERS='yellow',
    EMPHASIS='light blue',
    FILENAME='green',
    ID='green',
    DELIM='blue',
    ERROR='red',
    BAD_FORMAT='light red',
    WARNING='yellow',
    SUPPRESS='light black',
)


class _Logger:
    def __init__(self, params, /):
        self.message_cache = set()
        self._bidi_initialized = None
        self._encoding = params.get('encoding')
        self._logger = params.get('logger')
        self._no_warnings = params.get('no_warnings')
        self._verbosity = (
            'verbose' if params.get('verbose')
            else 'quiet' if params.get('quiet')
            else 'normal')
        self._ignoreerrors = params.get('ignoreerrors')

        stdout = sys.stderr if params.get('logtostderr') else sys.stdout
        self._out_files = Namespace(
            screen=sys.stderr if params.get('quiet') else stdout,
            out=stdout,
            error=sys.stderr,
        )

        try:
            windows_enable_vt_mode()
        except Exception as e:
            self.debug(f'Failed to enable VT mode: {e}')

        # hehe "immutable" namespace
        self._out_files.console = next(filter(supports_terminal_sequences, (sys.stderr, sys.stdout)), None)

        term_allow_color = os.getenv('TERM', '').lower() != 'dumb'
        base_no_color = bool(os.getenv('NO_COLOR'))

        def process_color_policy(stream):
            stream_name = {sys.stdout: 'stdout', sys.stderr: 'stderr'}[stream]
            policy = traverse_obj(params, ('color', (stream_name, None), {str}, any)) or 'auto'
            if policy in ('auto', 'auto-tty', 'no_color-tty'):
                no_color = base_no_color
                if policy.endswith('tty'):
                    no_color = policy.startswith('no_color')
                if term_allow_color and supports_terminal_sequences(stream):
                    return 'no_color' if no_color else True
                return False
            assert policy in ('always', 'never', 'no_color'), policy
            return {'always': True, 'never': False}.get(policy, policy)

        self._allow_colors = Namespace(**{
            name: process_color_policy(stream)
            for name, stream in self._out_files.items_ if name != 'console'
        })

    def screen(self, message, /):
        self._log(self._out_files.out, message)

    def debug(self, message, /, *, once=False):
        if self._verbosity != 'verbose':
            return
        message = f'[debug] {message}'
        if self._logger:
            self._logger.debug(message)
            return

        self.error(message, once=once)

    def info(self, message, /, quiet=False, *, newline=True, once=False):
        if self._logger:
            self._logger.debug(message)
            return

        suppress = (
            False if self._verbosity == 'verbose'
            else quiet if quiet is not None
            else self._verbosity == 'quiet')
        if not suppress:
            self._log(self._out_files.screen, message, newline=newline, once=once)

    def warning(self, message, /, *, once=False):
        if self._logger:
            self._logger.warning(message)
            return
        if self._no_warnings:
            return

        self.error(message, once=once, _prefix=self._format_err('WARNING:', _Styles.WARNING))

    def error(self, message: str, /, *, _prefix=None, once=False):
        if self._logger:
            self._logger.error(message)
            return

        self._log(self._out_files.error, message, once=once)

    def exception(self, message=None, /, prefix=True, tb=None):
        prefix = self._format_err('ERROR:', _Styles.ERROR) if prefix else None
        if message is not None:
            self.error(message, _prefix=prefix)
        if self._verbosity != 'verbose':
            return
        if tb is None:
            if sys.exc_info()[0]:  # if .exception has been called from an except block
                tb = ''
                if hasattr(sys.exc_info()[1], 'exc_info') and sys.exc_info()[1].exc_info[0]:
                    tb += ''.join(traceback.format_exception(*sys.exc_info()[1].exc_info))
                tb += encode_compat_str(traceback.format_exc())
            else:
                tb_data = traceback.format_list(traceback.extract_stack())
                tb = ''.join(tb_data)
        if tb:
            self.error(tb)

    def deprecation_warning(self, message, *, stacklevel=0):
        deprecation_warning(
            message, stacklevel=stacklevel + 1, printer=self.exception, is_error=False)

    def deprecated_feature(self, message):
        if self._logger:
            self._logger.warning(f'Deprecated Feature: {message}')
            return

        self.error(message, once=True, _prefix=self._format_err('Deprecated Feature:', _Styles.ERROR))

    def init_bidi_workaround(self, /):
        """
        Initialize the bidirectional workaround

        It raises `ImportError` on systems not providing the `pty` module
        (This is most notably the case on Windows machines).
        It also requires either `bidiv` or `fribidi` to be accessible.

        The width of the terminal will be collected once at startup only.
        If you need to update the terminal width passed to the executable
        call `init_bidi_workaround` after the resize, which will spawn a new
        bidi executable with the updated width.
        """
        try:
            self._init_bidi_workaround()
            self._bidi_initialized = True

        except Exception:
            self._bidi_initialized = False
            raise

    def _log(self, output, message, *, newline=True, once=False, prefix=None):
        assert isinstance(message, str)

        if prefix is not None:
            message = f'{prefix} {message}'

        if once:
            if message in self.message_cache:
                return
            self.message_cache.add(message)

        if self._bidi_initialized:
            message = self._apply_bidi_workaround(message)

        if newline:
            message += '\n'

        write_string(message, output, self._encoding)

    def _format_text(self, handle, allow_colors, text, f, fallback=None, *, test_encoding=False):
        # TODO: investigate this
        text = str(text)
        if test_encoding:
            original_text = text
            # handle.encoding can be None. See https://github.com/yt-dlp/yt-dlp/issues/2711
            encoding = self._encoding or getattr(handle, 'encoding', None) or 'ascii'
            text = text.encode(encoding, 'ignore').decode(encoding)
            if fallback is not None and text != original_text:
                text = fallback
        return format_text(text, f) if allow_colors is True else text if fallback is None else fallback

    def _format_out(self, *args, **kwargs):
        return self._format_text(self._out_files.out, self._allow_colors.out, *args, **kwargs)

    def _format_screen(self, *args, **kwargs):
        return self._format_text(self._out_files.screen, self._allow_colors.screen, *args, **kwargs)

    def _format_err(self, *args, **kwargs):
        return self._format_text(self._out_files.error, self._allow_colors.error, *args, **kwargs)

    def _init_bidi_workaround(self, /):
        import pty
        import shutil
        import subprocess
        from ..utils import Popen

        if self._bidi_initialized:
            self._bidi_reader.close()
            self._bidi_process.terminate()

        master, slave = pty.openpty()
        width = shutil.get_terminal_size().columns
        width_args = [] if not width else ['-w', str(width)]
        try:
            _output_process = Popen(
                ['bidiv', *width_args],
                stdin=subprocess.PIPE, stdout=slave, stderr=sys.stderr, encoding='utf-8')
        except OSError:
            _output_process = Popen(
                ['fribidi', '-c', 'UTF-8', *width_args],
                stdin=subprocess.PIPE, stdout=slave, stderr=sys.stderr, encoding='utf-8')

        assert _output_process.stdin is not None
        self._bidi_process = _output_process
        self._bidi_writer = _output_process.stdin
        self._bidi_reader = open(master, encoding='utf-8')

    def _apply_bidi_workaround(self, message):
        # `init_bidi_workaround()` MUST have been called prior.
        self._bidi_writer.write(f'{message}\n')
        self._bidi_writer.flush()

        line_count = message.count('\n') + 1
        return ''.join(self._bidi_reader.readlines(line_count))[:-1]
