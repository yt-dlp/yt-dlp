import inspect
import logging
import sys
import traceback


class deferred_class_attribute:
    def __init__(self, func):
        self.func = func

    def __get__(self, _, owner):
        result = self.func()
        setattr(owner, self.func.__name__, result)
        return result


class _YDLIgnoringLogger(logging.Logger):
    @deferred_class_attribute
    def _internal_frames():
        # XXX(output): Are these all the special cases?
        from . import logging as output_logging
        from ..downloader import common as downloader
        from ..extractor import common as extractor

        return frozenset(map(inspect.getabsfile, [
            _YDLIgnoringLogger,
            output_logging,
            logging,
            downloader,
            extractor,
        ]))

    @deferred_class_attribute
    def _ydl_path():
        from .. import YoutubeDL

        return inspect.getabsfile(YoutubeDL)

    @staticmethod
    def skip_frame(condition, start_frame):
        frame = start_frame
        if frame is None:
            return start_frame

        depth = 0
        while condition(frame, depth):
            depth += 1
            next_frame = frame.f_back
            if next_frame is None:
                return start_frame

            frame = next_frame

        return frame

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False,
             stacklevel=1):
        # TODO(output): This needs to handle exception reprocessing as well
        frame = inspect.currentframe()
        if frame is None:
            return

        def internal_frame(frame, _=...):
            return inspect.getabsfile(frame) in self._internal_frames

        # Skip internal frames
        frame = self.skip_frame(internal_frame, frame)

        # We need to skip additional frames since the
        # logging call could be delegated through YDL.
        # We look for the highest frame inside `YoutubeDL`,
        # then until it is no longer internal
        # so that `common` is skipped as well
        def ydl_frame(frame, _):
            return inspect.getabsfile(frame) != self._ydl_path

        above_ydl_frame = self.skip_frame(ydl_frame, frame).f_back
        if above_ydl_frame is not None and internal_frame(above_ydl_frame):
            frame = self.skip_frame(internal_frame, above_ydl_frame)

        # Skip `stacklevel` amount of levels
        # XXX(output): Could be f_back instead since stacklevel should == 1
        frame = self.skip_frame(lambda _, depth: depth == stacklevel, frame)

        fn, lno, func, *_ = inspect.getframeinfo(frame)

        module = inspect.getmodule(frame.f_code)
        name = self.name if module is None else module.__name__

        sinfo = None
        if stack_info:
            sinfo = f'Stack (most recent call last):\n{traceback.format_stack()}'
            if sinfo.endswith('\n'):
                sinfo = sinfo[:-1]

        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()

        self.handle(self.makeRecord(
            name, level, fn, lno, msg, args,
            exc_info, func, extra, sinfo))


logging.setLoggerClass(_YDLIgnoringLogger)
logger = logging.getLogger('yt_dlp')
logging.setLoggerClass(logging.Logger)
