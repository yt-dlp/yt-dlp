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
    es6_tcc = 'player_es6_tcc.vflset/en_US/base.js'
    es6_tce = 'player_es6_tce.vflset/en_US/base.js'
    tv = 'tv-player-ias.vflset/tv-player-ias.js'
    tv_es6 = 'tv-player-es6.vflset/tv-player-es6.js'
    phone = 'player-plasma-ias-phone-en_US.vflset/base.js'
    house = 'house_brand_player.vflset/en_US/base.js'


@dataclasses.dataclass
class Challenge:
    player: str
    variant: Variant
    type: JsChallengeType
    values: dict[str, str] = dataclasses.field(default_factory=dict)

    def url(self, /):
        return f'https://www.youtube.com/s/player/{self.player}/{self.variant.value}'


CHALLENGES: list[Challenge] = [
    # 20518
    Challenge('edc3ba07', Variant.tv, JsChallengeType.N, {
        'BQoJvGBkC2nj1ZZLK-': '-m-se9fQVnvEofLx',
    }),
    Challenge('edc3ba07', Variant.tv, JsChallengeType.SIG, {
        'NJAJEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyyPRt=BM8-XO5tm5hlMCSVpAiEAv7eP3CURqZNSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=gwzz':
            'zwg=wgwCHlydB9zg7PMegXoVzaoAXXB8woPSNZqRUC3Pe7vAEiApVSCMlh5mt5OX-8MB=tRPyyEdAM9MPM-kPfjgTxEK0IAhIgRwE0jiz',
    }),
    # 20521
    Challenge('316b61b4', Variant.tv, JsChallengeType.N, {
        'IlLiA21ny7gqA2m4p37': 'GchRcsUC_WmnhOUVGV',
    }),
    Challenge('316b61b4', Variant.tv, JsChallengeType.SIG, {
        'NJAJEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyyPRt=BM8-XO5tm5hlMCSVpAiEAv7eP3CURqZNSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=gwzz':
            'tJAJEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyyPRN=BM8-XO5tm5hlMCSVpAiEAv7eP3CURqZNSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=gwz',
    }),
    # 20522
    Challenge('74edf1a3', Variant.tv, JsChallengeType.N, {
        'IlLiA21ny7gqA2m4p37': '9nRTxrbM1f0yHg',
        'eabGFpsUKuWHXGh6FR4': 'izmYqDEY6kl7Sg',
    }),
    Challenge('74edf1a3', Variant.tv, JsChallengeType.SIG, {
        'NJAJEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyyPRt=BM8-XO5tm5hlMCSVpAiEAv7eP3CURqZNSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=gwzz':
            'NJAJEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyyPRt=BM8-XO5tm5hzMCSVpAiEAv7eP3CURqZNSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=gwzl',
    }),
    # 20523
    Challenge('901741ab', Variant.tv, JsChallengeType.N, {
        'BQoJvGBkC2nj1ZZLK-': 'UMPovvBZRh-sjb',
    }),
    Challenge('901741ab', Variant.tv, JsChallengeType.SIG, {
        'NJAJEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyyPRt=BM8-XO5tm5hlMCSVpAiEAv7eP3CURqZNSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=gwzz':
            'wgwCHlydB9Hg7PMegXoVzaoAXXB8woPSNZqRUC3Pe7vAEiApVSCMlhwmt5ON-8MB=5RPyyzdAM9MPM-kPfjgTxEK0IAhIgRwE0jiEJA',
    }),
    # 20524
    Challenge('e7573094', Variant.tv, JsChallengeType.N, {
        'IlLiA21ny7gqA2m4p37': '3KuQ3235dojTSjo4',
    }),
    Challenge('e7573094', Variant.tv, JsChallengeType.SIG, {
        'NJAJEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyyPRt=BM8-XO5tm5hlMCSVpAiEAv7eP3CURqZNSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=gwzz':
            'yEij0EwRgIhAI0KExTgjfPk-MPM9MAdzyNPRt=BM8-XO5tm5hlMCSVNAiEAvpeP3CURqZJSPow8BXXAoazVoXgeMP7gH9BdylHCwgw=g',
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
