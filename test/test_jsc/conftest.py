from unittest.mock import MagicMock

import pytest

import yt_dlp.globals
from yt_dlp import YoutubeDL
from yt_dlp.extractor.common import InfoExtractor


@pytest.fixture
def ie() -> InfoExtractor:
    runtime_names = yt_dlp.globals.supported_js_runtimes.value
    ydl = YoutubeDL({'js_runtimes': {key: {} for key in runtime_names}})
    return ydl.get_info_extractor('Youtube')


@pytest.fixture
def logger():
    return MagicMock()
