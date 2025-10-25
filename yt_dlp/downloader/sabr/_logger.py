from __future__ import annotations

from yt_dlp.utils import format_field, traverse_obj
from yt_dlp.extractor.youtube._streaming.sabr.models import SabrLogger
from yt_dlp.utils._utils import _YDLLogger

# TODO: create a logger that logs to a file rather than the console.
#  Might be useful for debugging SABR issues from users.


class SabrFDLogger(SabrLogger):
    def __init__(self, ydl, prefix, log_level: SabrLogger.LogLevel | None = None):
        self._ydl_logger = _YDLLogger(ydl)
        self.prefix = prefix
        self.log_level = log_level if log_level is not None else self.LogLevel.INFO

    def _format_msg(self, message: str):
        prefixstr = format_field(self.prefix, None, '[%s] ')
        return f'{prefixstr}{message}'

    def trace(self, message: str):
        if self.log_level <= self.LogLevel.TRACE:
            self._ydl_logger.debug(self._format_msg('TRACE: ' + message))

    def debug(self, message: str):
        if self.log_level <= self.LogLevel.DEBUG:
            self._ydl_logger.debug(self._format_msg(message))

    def info(self, message: str):
        if self.log_level <= self.LogLevel.INFO:
            self._ydl_logger.info(self._format_msg(message))

    def warning(self, message: str, *, once=False):
        if self.log_level <= self.LogLevel.WARNING:
            self._ydl_logger.warning(self._format_msg(message), once=once)

    def error(self, message: str):
        if self.log_level <= self.LogLevel.ERROR:
            self._ydl_logger.error(self._format_msg(message), is_error=False)


def create_sabrfd_logger(ydl, prefix):
    return SabrFDLogger(
        ydl, prefix=prefix,
        log_level=SabrFDLogger.LogLevel(traverse_obj(
            ydl.params, ('extractor_args', 'youtube', 'sabr_log_level', 0, {str}), get_all=False)))
