import errno
import sys

from .logging import Verbosity, Logger
from ..utils import DownloadError, windows_enable_vt_mode


def make_logger(params):
    screen = sys.stderr if params.get('logtostderr') else sys.stdout
    stdout = sys.stderr if params.get('quiet') else screen
    verbosity = (
        Verbosity.VERBOSE if params.get('verbose')
        else Verbosity.QUIET if params.get('quiet')
        else Verbosity.NORMAL)

    use_term_codes = not params.get('no_color', False)
    if use_term_codes:
        use_term_codes = None
    logger = Logger(
        screen, verbosity, encoding=params.get('encoding'),
        use_term_codes=use_term_codes, disable_progress=bool(params.get('noprogress')))

    logger_param = params.get('logger')
    if logger_param == 'logging':
        logger.setup_logging_logger()
    elif logger_param:
        logger.setup_class_logger(logger_param)
    else:
        logger.setup_stream_logger(stdout, sys.stderr, no_warnings=params.get('no_warnings', False))

    return logger


def wrap_debug(logger):
    def debug(func):
        def wrapper(message, once=True):
            func(f'[debug] {message}', once=once)

        return wrapper

    _debug_wrap_indicator = '__ydl_debug_wrapped'
    if not getattr(logger, _debug_wrap_indicator, None):
        logger = logger.make_derived(debug=debug)
        setattr(logger, _debug_wrap_indicator, True)

    return logger


def _wrap_handle_error(ydl, logger):
    ignore_errors = bool(ydl.params.get('ignoreerrors'))

    def handle_error(func):
        def wrapper(message, tb=None, is_error=True, prefix=True):
            func(message, tb=tb, is_error=is_error, prefix=prefix)
            if not is_error:
                return
            if not ignore_errors:
                raise DownloadError(message, sys.exc_info())

            ydl._download_retcode = 1

        return wrapper

    _error_wrap_indicator = '__ydl_error_wrapped'
    if not getattr(logger, _error_wrap_indicator, None):
        logger = logger.make_derived(handle_error=handle_error)
        setattr(logger, _error_wrap_indicator, True)

    return logger


def _setup_bidi(logger):
    if logger.bidi_initialized is not None:
        return

    from .. import _IN_CLI
    name = '--bidi-workaround' if _IN_CLI else 'bidi_workaround parameter'
    try:
        logger.init_bidi_workaround()

    except OSError as ose:
        if ose.errno != errno.ENOENT:
            raise

        logger.warning(
            f'Could not find any bidi executable, ignoring {name}. '
            'Make sure that either bidiv or fribidi are available as executables in your $PATH.')

    except ImportError:
        logger.warning(f'Could not import pty (perhaps not on *nix?), ignoring {name}.')


def _make_ydl_logger(params):
    error = None
    try:
        windows_enable_vt_mode()
    except Exception as e:
        error = e

    logger = wrap_debug(make_logger(params))
    if error:
        logger.debug(f'Failed to enable VT mode: {error}')

    return logger
