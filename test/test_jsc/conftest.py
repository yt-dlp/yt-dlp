import re
import pathlib
from unittest.mock import MagicMock

import pytest

import yt_dlp.globals
from yt_dlp import YoutubeDL
from yt_dlp.extractor.common import InfoExtractor


_TESTDATA_PATH = pathlib.Path(__file__).parent.parent / 'testdata/sigs'
_player_re = re.compile(r'^.+/player/(?P<id>[a-zA-Z0-9_/.-]+)\.js$')
_player_id_trans = str.maketrans(dict.fromkeys('/.-', '_'))


@pytest.fixture
def ie() -> InfoExtractor:
    runtime_names = yt_dlp.globals.supported_js_runtimes.value
    ydl = YoutubeDL({'js_runtimes': {key: {} for key in runtime_names}})
    ie = ydl.get_info_extractor('Youtube')

    def _load_player(video_id, player_url, fatal=True):
        match = _player_re.match(player_url)
        test_id = match.group('id').translate(_player_id_trans)
        cached_file = _TESTDATA_PATH / f'player-{test_id}.js'

        if cached_file.exists():
            return cached_file.read_text()

        if code := ie._download_webpage(player_url, video_id, fatal=fatal):
            _TESTDATA_PATH.mkdir(exist_ok=True, parents=True)
            cached_file.write_text(code)
            return code

        return None

    ie._load_player = _load_player
    return ie


@pytest.fixture
def logger():
    return MagicMock()
