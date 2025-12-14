from __future__ import annotations

import dataclasses
import enum
import importlib.util
import json

import pytest

from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeRequest,
    JsChallengeType,
    JsChallengeProviderResponse,
    JsChallengeResponse,
    NChallengeInput,
    NChallengeOutput,
    SigChallengeInput,
    SigChallengeOutput,
)
from yt_dlp.extractor.youtube.jsc._builtin.bun import BunJCP
from yt_dlp.extractor.youtube.jsc._builtin.deno import DenoJCP
from yt_dlp.extractor.youtube.jsc._builtin.node import NodeJCP
from yt_dlp.extractor.youtube.jsc._builtin.quickjs import QuickJSJCP


_has_ejs = bool(importlib.util.find_spec('yt_dlp_ejs'))
pytestmark = pytest.mark.skipif(not _has_ejs, reason='yt-dlp-ejs not available')


class Variant(enum.Enum):
    main = 'player_ias.vflset/en_US/base.js'
    tcc = 'player_ias_tcc.vflset/en_US/base.js'
    tce = 'player_ias_tce.vflset/en_US/base.js'
    es5 = 'player_es5.vflset/en_US/base.js'
    es6 = 'player_es6.vflset/en_US/base.js'
    tv = 'tv-player-ias.vflset/tv-player-ias.js'
    tv_es6 = 'tv-player-es6.vflset/tv-player-es6.js'
    phone = 'player-plasma-ias-phone-en_US.vflset/base.js'
    tablet = 'player-plasma-ias-tablet-en_US.vflset/base.js'


@dataclasses.dataclass
class Challenge:
    player: str
    variant: Variant
    type: JsChallengeType
    values: dict[str, str] = dataclasses.field(default_factory=dict)

    def url(self, /):
        return f'https://www.youtube.com/s/player/{self.player}/{self.variant.value}'


CHALLENGES: list[Challenge] = [
    Challenge('3d3ba064', Variant.tce, JsChallengeType.N, {
        'ZdZIqFPQK-Ty8wId': 'qmtUsIz04xxiNW',
        '4GMrWHyKI5cEvhDO': 'N9gmEX7YhKTSmw',
    }),
    Challenge('3d3ba064', Variant.tce, JsChallengeType.SIG, {
        'gN7a-hudCuAuPH6fByOk1_GNXN0yNMHShjZXS2VOgsEItAJz0tipeavEOmNdYN-wUtcEqD3bCXjc0iyKfAyZxCBGgIARwsSdQfJ2CJtt':
            'ttJC2JfQdSswRAIgGBCxZyAfKyi0cjXCb3gqEctUw-NYdNmOEvaepit0zJAtIEsgOV2SXZjhSHMNy0NXNG_1kNyBf6HPuAuCduh-a7O',
    }),
    Challenge('5ec65609', Variant.tce, JsChallengeType.N, {
        '0eRGgQWJGfT5rFHFj': '4SvMpDQH-vBJCw',
    }),
    Challenge('5ec65609', Variant.tce, JsChallengeType.SIG, {
        'AAJAJfQdSswRQIhAMG5SN7-cAFChdrE7tLA6grH0rTMICA1mmDc0HoXgW3CAiAQQ4=CspfaF_vt82XH5yewvqcuEkvzeTsbRuHssRMyJQ=I':
            'AJfQdSswRQIhAMG5SN7-cAFChdrE7tLA6grI0rTMICA1mmDc0HoXgW3CAiAQQ4HCspfaF_vt82XH5yewvqcuEkvzeTsbRuHssRMyJQ==',
    }),
    Challenge('6742b2b9', Variant.tce, JsChallengeType.N, {
        '_HPB-7GFg1VTkn9u': 'qUAsPryAO_ByYg',
        'K1t_fcB6phzuq2SF': 'Y7PcOt3VE62mog',
    }),
    Challenge('6742b2b9', Variant.tce, JsChallengeType.SIG, {
        'MMGZJMUucirzS_SnrSPYsc85CJNnTUi6GgR5NKn-znQEICACojE8MHS6S7uYq4TGjQX_D4aPk99hNU6wbTvorvVVMgIARwsSdQfJAA':
            'AJfQdSswRAIgMVVvrovTbw6UNh99kPa4D_XQjGT4qYu7S6SHM8EjoCACIEQnz-nKN5RgG6iUTnNJC58csYPSrnS_SzricuUMJZGM',
    }),
    Challenge('2b83d2e0', Variant.main, JsChallengeType.N, {
        '0eRGgQWJGfT5rFHFj': 'euHbygrCMLksxd',
    }),
    Challenge('2b83d2e0', Variant.main, JsChallengeType.SIG, {
        'MMGZJMUucirzS_SnrSPYsc85CJNnTUi6GgR5NKn-znQEICACojE8MHS6S7uYq4TGjQX_D4aPk99hNU6wbTvorvVVMgIARwsSdQfJA':
            '-MGZJMUucirzS_SnrSPYsc85CJNnTUi6GgR5NKnMznQEICACojE8MHS6S7uYq4TGjQX_D4aPk99hNU6wbTvorvVVMgIARwsSdQfJ',
    }),
    Challenge('638ec5c6', Variant.main, JsChallengeType.N, {
        'ZdZIqFPQK-Ty8wId': '1qov8-KM-yH',
    }),
    Challenge('638ec5c6', Variant.main, JsChallengeType.SIG, {
        'gN7a-hudCuAuPH6fByOk1_GNXN0yNMHShjZXS2VOgsEItAJz0tipeavEOmNdYN-wUtcEqD3bCXjc0iyKfAyZxCBGgIARwsSdQfJ2CJtt':
            'MhudCuAuP-6fByOk1_GNXN7gNHHShjyXS2VOgsEItAJz0tipeav0OmNdYN-wUtcEqD3bCXjc0iyKfAyZxCBGgIARwsSdQfJ2CJtt',
    }),
]

requests: list[JsChallengeRequest] = []
responses: list[JsChallengeProviderResponse] = []
for test in CHALLENGES:
    input_type, output_type = {
        JsChallengeType.N: (NChallengeInput, NChallengeOutput),
        JsChallengeType.SIG: (SigChallengeInput, SigChallengeOutput),
    }[test.type]

    request = JsChallengeRequest(test.type, input_type(test.url(), list(test.values.keys())), test.player)
    requests.append(request)
    responses.append(JsChallengeProviderResponse(request, JsChallengeResponse(test.type, output_type(test.values))))


@pytest.fixture(params=[BunJCP, DenoJCP, NodeJCP, QuickJSJCP])
def jcp(request, ie, logger):
    obj = request.param(ie, logger, None)
    if not obj.is_available():
        pytest.skip(f'{obj.PROVIDER_NAME} is not available')
    obj.is_dev = True
    return obj


@pytest.mark.download
def test_bulk_requests(jcp):
    assert list(jcp.bulk_solve(requests)) == responses


@pytest.mark.download
def test_using_cached_player(jcp):
    first_player_requests = requests[:3]
    player = jcp._get_player(first_player_requests[0].video_id, first_player_requests[0].input.player_url)
    initial = json.loads(jcp._run_js_runtime(jcp._construct_stdin(player, False, first_player_requests)))
    preprocessed = initial.pop('preprocessed_player')
    result = json.loads(jcp._run_js_runtime(jcp._construct_stdin(preprocessed, True, first_player_requests)))

    assert initial == result
