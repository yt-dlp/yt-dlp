from __future__ import annotations

import json

import pytest
try:
    import yt_dlp_ejs
except ImportError:
    yt_dlp_ejs = None

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


pytestmark = pytest.mark.skipif(not yt_dlp_ejs, reason='yt-dlp-ejs not available')

TESTS = [
    JsChallengeRequest(JsChallengeType.N, NChallengeInput('https://www.youtube.com/s/player/3d3ba064/player_ias_tce.vflset/en_US/base.js', [
        'ZdZIqFPQK-Ty8wId',
        '4GMrWHyKI5cEvhDO',
    ])),
    JsChallengeRequest(JsChallengeType.SIG, SigChallengeInput('https://www.youtube.com/s/player/3d3ba064/player_ias_tce.vflset/en_US/base.js', [
        'gN7a-hudCuAuPH6fByOk1_GNXN0yNMHShjZXS2VOgsEItAJz0tipeavEOmNdYN-wUtcEqD3bCXjc0iyKfAyZxCBGgIARwsSdQfJ2CJtt',
    ])),
    JsChallengeRequest(JsChallengeType.N, NChallengeInput('https://www.youtube.com/s/player/5ec65609/player_ias_tce.vflset/en_US/base.js', [
        '0eRGgQWJGfT5rFHFj',
    ])),
    JsChallengeRequest(JsChallengeType.SIG, SigChallengeInput('https://www.youtube.com/s/player/5ec65609/player_ias_tce.vflset/en_US/base.js', [
        'AAJAJfQdSswRQIhAMG5SN7-cAFChdrE7tLA6grH0rTMICA1mmDc0HoXgW3CAiAQQ4=CspfaF_vt82XH5yewvqcuEkvzeTsbRuHssRMyJQ=I',
    ])),
    JsChallengeRequest(JsChallengeType.N, NChallengeInput('https://www.youtube.com/s/player/6742b2b9/player_ias_tce.vflset/en_US/base.js', [
        '_HPB-7GFg1VTkn9u',
        'K1t_fcB6phzuq2SF',
    ])),
    JsChallengeRequest(JsChallengeType.SIG, SigChallengeInput('https://www.youtube.com/s/player/6742b2b9/player_ias_tce.vflset/en_US/base.js', [
        'MMGZJMUucirzS_SnrSPYsc85CJNnTUi6GgR5NKn-znQEICACojE8MHS6S7uYq4TGjQX_D4aPk99hNU6wbTvorvVVMgIARwsSdQfJAA',
    ])),
]

RESPONSES = [
    JsChallengeProviderResponse(test, JsChallengeResponse(test.type, (
        NChallengeOutput if test.type is JsChallengeType.N else SigChallengeOutput
    )(dict(zip(test.input.challenges, results, strict=True)))))
    for test, results in zip(TESTS, [
        ['qmtUsIz04xxiNW', 'N9gmEX7YhKTSmw'],
        ['ttJC2JfQdSswRAIgGBCxZyAfKyi0cjXCb3gqEctUw-NYdNmOEvaepit0zJAtIEsgOV2SXZjhSHMNy0NXNG_1kNyBf6HPuAuCduh-a7O'],
        ['4SvMpDQH-vBJCw'],
        ['AJfQdSswRQIhAMG5SN7-cAFChdrE7tLA6grI0rTMICA1mmDc0HoXgW3CAiAQQ4HCspfaF_vt82XH5yewvqcuEkvzeTsbRuHssRMyJQ=='],
        ['qUAsPryAO_ByYg', 'Y7PcOt3VE62mog'],
        ['AJfQdSswRAIgMVVvrovTbw6UNh99kPa4D_XQjGT4qYu7S6SHM8EjoCACIEQnz-nKN5RgG6iUTnNJC58csYPSrnS_SzricuUMJZGM'],
    ], strict=True)
]


@pytest.fixture(params=[BunJCP, DenoJCP, NodeJCP])
def jcp(request, ie, logger):
    obj = request.param(ie, logger, None)
    if not obj.is_available():
        pytest.skip(f'{obj.PROVIDER_NAME} is not available')
    obj.is_dev = True
    return obj


@pytest.mark.download
def test_bulk_requests(jcp):
    assert list(jcp.bulk_solve(TESTS)) == RESPONSES


@pytest.mark.download
def test_using_cached_player(jcp):
    requests = TESTS[:3]
    player = jcp._get_player(requests[0].video_id, requests[0].input.player_url)
    initial = json.loads(jcp._run_js_runtime(jcp._construct_stdin(player, False, requests)))
    preprocessed = initial.pop('preprocessed_player')
    result = json.loads(jcp._run_js_runtime(jcp._construct_stdin(preprocessed, True, requests)))

    assert initial == result
