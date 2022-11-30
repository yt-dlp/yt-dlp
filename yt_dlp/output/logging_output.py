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
    def skip_frames(condition, start_frame):
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

    @staticmethod
    def _get_raising_frame():
        error = sys.exc_info()[1]
        if error is None:
            return None

        error_chain = [error]

        while error is not None:
            error_chain.append(error)
            error = error.__cause__ or error.__context__

        for error in reversed(error_chain):
            tb = error.__traceback__
            if tb is None:
                continue
            while tb.tb_next is not None:
                tb = tb.tb_next

            return tb.tb_frame

        return None

    @classmethod
    def _get_logging_frame(cls, stacklevel):
        frame = inspect.currentframe()
        if frame is None:
            return None

        def internal_frame(frame, _):
            return inspect.getabsfile(frame) in cls._internal_frames

        frame = cls.skip_frames(internal_frame, frame)

        # We need to skip additional frames since the
        # logging call could be delegated through YDL.
        # We look for the highest frame inside `YoutubeDL`,
        # then until it is no longer internal
        # so that `common` is skipped as well
        def ydl_frame(frame, _):
            return inspect.getabsfile(frame) != cls._ydl_path

        above_ydl_frame = cls.skip_frames(ydl_frame, frame).f_back
        # Assumption: YoutubeDL.py is never main
        assert above_ydl_frame is not None
        frame = cls.skip_frames(internal_frame, above_ydl_frame)

        # Skip `stacklevel` amount of levels
        frame = cls.skip_frames(lambda _, depth: depth == stacklevel, frame)

        return frame

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False,
             stacklevel=1):
        frame = self._get_raising_frame() or self._get_logging_frame(stacklevel)
        if frame is None:
            return

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
