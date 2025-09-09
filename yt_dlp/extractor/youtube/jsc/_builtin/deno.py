from __future__ import annotations

import collections
import json
import subprocess

from yt_dlp.extractor.youtube.jsc._builtin.runtime import JsRuntimeJCPBase
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeProviderResponse,
    JsChallengeRequest,
    JsChallengeResponse,
    JsChallengeType,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.utils import Popen

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Generator


@register_provider
class DenoJCP(JsRuntimeJCPBase, BuiltinIEContentProvider):
    PROVIDER_NAME = 'deno'
    JS_RUNTIME_NAME = 'deno'
    _SUPPORTED_TYPES = [JsChallengeType.NSIG, JsChallengeType.SIG]

    _DENO_ARGS = ['--location', 'https://www.youtube.com/watch?v=yt-dlp-wins', '--no-prompt']
    _SUPPORTED_VERSION = '0.0.1'
    # TODO: insert correct hash here
    _SUPPORTED_HASH = 'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26'
    _RELEASE_BUNDLE_URL = f'https://github.com/yt-dlp/yt-dlp-jsc-deno/releases/download/{_SUPPORTED_VERSION}/jsc-deno.js'

    def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> Generator[JsChallengeProviderResponse, None, None]:
        deno = self.runtime_info.path
        self.logger.trace(f'Using deno: {deno}')
        cmd = [deno, *self._DENO_ARGS]

        grouped = collections.defaultdict(list)
        for request in requests:
            grouped[request.player_url].append(request)

        with self._bundle.path() as path:
            self.logger.trace(f'Using bundle at {path}')
            cmd.append(str(path))

            for player_url, requests in grouped.items():
                cached = False
                if cached:
                    code = self.ie.cache['something']
                else:
                    code = self._get_player(requests[0].video_id, player_url)
                responses, preprocessed = self._call_deno_bundle(cmd, requests, code, preprocessed=cached)
                if not cached:
                    # TODO: cache preprocessed
                    _ = preprocessed
                yield from responses

    def _call_deno_bundle(
        self,
        /,
        cmd: list[str],
        requests: list[JsChallengeRequest],
        player: str,
        preprocessed: bool,
    ) -> tuple[list[JsChallengeProviderResponse], str | None]:
        # TODO: update for new request structure
        json_requests = [{
            'type': request.type.value,
            'challenge': request.challenge,
            'player_url': request.player_url,
            'video_id': request.video_id,
        } for request in requests]
        json_input = {
            'type': 'preprocessed',
            'preprocessed_player': player,
            'requests': json_requests,
        } if preprocessed else {
            'type': 'player',
            'player': player,
            'requests': json_requests,
            'output_preprocessed': True,
        }
        with Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate_or_kill(json.dumps(json_input))
            if proc.returncode or stderr:
                raise JsChallengeProviderError('Error running deno process')

        json_response = json.loads(stdout)
        if json_response['type'] == 'error':
            raise JsChallengeProviderError(json_response['error'])

        responses = []
        for response in json_response['responses']:
            response['request']['type'] = JsChallengeType(response['request']['type'])
            request = JsChallengeRequest(**response['request'])
            responses.append(
                JsChallengeProviderResponse(request, None, response['error']) if response['type'] == 'error'
                else JsChallengeProviderResponse(request, JsChallengeResponse(response['response'], request)),
            )
        if preprocessed:
            return responses, None

        return responses, json_response['preprocessed_player']


@register_preference(DenoJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 1000
