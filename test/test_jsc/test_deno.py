from __future__ import annotations

import pytest
try:
    import yt_dlp_jsc_deno
except ImportError:
    yt_dlp_jsc_deno = None

from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeRequest,
    JsChallengeType,
    JsChallengeProviderResponse,
    JsChallengeResponse,
)
from yt_dlp.extractor.youtube.jsc._builtin.deno import DenoJCP


@pytest.mark.skipif(not yt_dlp_jsc_deno, reason='yt-dlp-jsc-deno not available')
class TestDenoJCP:
    TESTS = [
        JsChallengeRequest(JsChallengeType.NSIG, 'ZdZIqFPQK-Ty8wId', 'https://www.youtube.com/s/player/3d3ba064/player_ias_tce.vflset/en_US/base.js', 'test1'),
        JsChallengeRequest(JsChallengeType.NSIG, '4GMrWHyKI5cEvhDO', 'https://www.youtube.com/s/player/3d3ba064/player_ias_tce.vflset/en_US/base.js', 'test2'),
        JsChallengeRequest(JsChallengeType.SIG, 'gN7a-hudCuAuPH6fByOk1_GNXN0yNMHShjZXS2VOgsEItAJz0tipeavEOmNdYN-wUtcEqD3bCXjc0iyKfAyZxCBGgIARwsSdQfJ2CJtt', 'https://www.youtube.com/s/player/3d3ba064/player_ias_tce.vflset/en_US/base.js', 'test3'),
        JsChallengeRequest(JsChallengeType.NSIG, '0eRGgQWJGfT5rFHFj', 'https://www.youtube.com/s/player/5ec65609/player_ias_tce.vflset/en_US/base.js', 'test4'),
        JsChallengeRequest(JsChallengeType.SIG, 'AAJAJfQdSswRQIhAMG5SN7-cAFChdrE7tLA6grH0rTMICA1mmDc0HoXgW3CAiAQQ4=CspfaF_vt82XH5yewvqcuEkvzeTsbRuHssRMyJQ=I', 'https://www.youtube.com/s/player/5ec65609/player_ias_tce.vflset/en_US/base.js', 'test5'),
        JsChallengeRequest(JsChallengeType.NSIG, '_HPB-7GFg1VTkn9u', 'https://www.youtube.com/s/player/6742b2b9/player_ias_tce.vflset/en_US/base.js', 'test6'),
        JsChallengeRequest(JsChallengeType.NSIG, 'K1t_fcB6phzuq2SF', 'https://www.youtube.com/s/player/6742b2b9/player_ias_tce.vflset/en_US/base.js', 'test7'),
        JsChallengeRequest(JsChallengeType.SIG, 'MMGZJMUucirzS_SnrSPYsc85CJNnTUi6GgR5NKn-znQEICACojE8MHS6S7uYq4TGjQX_D4aPk99hNU6wbTvorvVVMgIARwsSdQfJAA', 'https://www.youtube.com/s/player/6742b2b9/player_ias_tce.vflset/en_US/base.js', 'test8'),
    ]
    RESPONSES = [
        JsChallengeProviderResponse(TESTS[0], JsChallengeResponse('qmtUsIz04xxiNW', TESTS[0])),
        JsChallengeProviderResponse(TESTS[1], JsChallengeResponse('N9gmEX7YhKTSmw', TESTS[1])),
        JsChallengeProviderResponse(TESTS[2], JsChallengeResponse('ttJC2JfQdSswRAIgGBCxZyAfKyi0cjXCb3gqEctUw-NYdNmOEvaepit0zJAtIEsgOV2SXZjhSHMNy0NXNG_1kNyBf6HPuAuCduh-a7O', TESTS[2])),
        JsChallengeProviderResponse(TESTS[3], JsChallengeResponse('4SvMpDQH-vBJCw', TESTS[3])),
        JsChallengeProviderResponse(TESTS[4], JsChallengeResponse('AJfQdSswRQIhAMG5SN7-cAFChdrE7tLA6grI0rTMICA1mmDc0HoXgW3CAiAQQ4HCspfaF_vt82XH5yewvqcuEkvzeTsbRuHssRMyJQ==', TESTS[4])),
        JsChallengeProviderResponse(TESTS[5], JsChallengeResponse('qUAsPryAO_ByYg', TESTS[5])),
        JsChallengeProviderResponse(TESTS[6], JsChallengeResponse('Y7PcOt3VE62mog', TESTS[6])),
        JsChallengeProviderResponse(TESTS[7], JsChallengeResponse('AJfQdSswRAIgMVVvrovTbw6UNh99kPa4D_XQjGT4qYu7S6SHM8EjoCACIEQnz-nKN5RgG6iUTnNJC58csYPSrnS_SzricuUMJZGM', TESTS[7])),
    ]

    @pytest.fixture
    def jcp(self, ie, logger) -> DenoJCP:
        return DenoJCP(ie, logger, settings={})

    def test_bulk_requests(self, jcp: DenoJCP):
        assert jcp.bulk_solve(self.TESTS) == self.RESPONSES

    def test_using_cached_player(self, jcp: DenoJCP):
        requests = self.TESTS[:3]
        with yt_dlp_jsc_deno.path() as path:
            cmd = ['deno', *jcp._DENO_ARGS, str(path)]

            code = jcp._get_player(requests[0].video_id, requests[0].player_url)
            print('call 1')
            responses_uncached, preprocessed = jcp._call_deno_bundle(cmd, requests, code, preprocessed=False)
            print('call 2')
            responses, _ = jcp._call_deno_bundle(cmd, requests, preprocessed, preprocessed=True)
            print('call 3')

        assert responses == responses_uncached
        assert responses == self.RESPONSES[:3]
