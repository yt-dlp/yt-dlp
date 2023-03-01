import errno
import inspect
import sys
import warnings

from .logger import Logger, Verbosity
from ..utils import windows_enable_vt_mode


def redirect_warnings(logger):
    """Redirect messages from the `warnings` module to a `Logger`"""
    _old_showwarning = warnings.showwarning

    def _warnings_showwarning(message, category, filename, lineno, file=None, line=None):
        if file is not None:
            _old_showwarning(message, category, filename, lineno, file, line)
            return

        module = inspect.getmodule(None, filename)
        if module:
            filename = module.__name__
        logger.warning(f'{category.__name__} ({filename}:{lineno}): {message}')

    warnings.showwarning = _warnings_showwarning


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
        logger.setup_logging_outputs()
    elif logger_param:
        logger.setup_class_outputs(logger_param)
    else:
        logger.setup_stream_outputs(stdout, sys.stderr, no_warnings=params.get('no_warnings', False))

    return logger


def wrap_debug(logger):
    def debug(func):
        def wrapper(message, once=True):
            func(f'[debug] {message}', once=once)

        return wrapper

    _debug_wrap_indicator = '__ydl_debug_wrapped'
    if not getattr(logger, _debug_wrap_indicator, None):
        logger = logger.derive(debug=debug)
        setattr(logger, _debug_wrap_indicator, True)

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
