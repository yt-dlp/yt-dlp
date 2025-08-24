import collections

import pytest

from yt_dlp import YoutubeDL
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.extractor.youtube.pot._provider import IEContentProviderLogger


class MockLogger(IEContentProviderLogger):
    log_level = IEContentProviderLogger.LogLevel.TRACE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages = collections.defaultdict(list)

    def trace(self, message: str):
        self.messages['trace'].append(message)

    def debug(self, message: str):
        self.messages['debug'].append(message)

    def info(self, message: str):
        self.messages['info'].append(message)

    def warning(self, message: str, *, once=False):
        self.messages['warning'].append(message)

    def error(self, message: str):
        self.messages['error'].append(message)


@pytest.fixture
def ie() -> InfoExtractor:
    ydl = YoutubeDL()
    return ydl.get_info_extractor('Youtube')


@pytest.fixture
def logger() -> MockLogger:
    return MockLogger()
