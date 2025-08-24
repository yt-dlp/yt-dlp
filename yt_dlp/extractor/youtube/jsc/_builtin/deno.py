from __future__ import annotations

import collections
import json
import subprocess

try:
    import yt_dlp_jsc_deno
except ImportError:
    yt_dlp_jsc_deno = None

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
from yt_dlp.utils import Popen

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Generator


@register_provider
class DenoJCP(JsChallengeProvider):
    PROVIDER_NAME = 'yt_dlp_jsc_deno'
    PROVIDER_VERSION = yt_dlp_jsc_deno.version if yt_dlp_jsc_deno else 'unknown'
    BUG_REPORT_LOCATION = 'https://github.com/yt-dlp/yt-dlp-jsc-deno'
    _SUPPORTED_TYPES = None

    _DENO_ARGS = ['--location', 'https://www.youtube.com/watch?v=yt-dlp-wins', '--no-prompt', '--allow-env']

    def is_available(self) -> bool:
        return yt_dlp_jsc_deno and yt_dlp_jsc_deno.exists()

    def _real_solve(self, request: JsChallengeRequest) -> JsChallengeResponse:
        assert False, 'jank ass incomplete poc'

    def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> list[JsChallengeProviderResponse]:
        try:
            return list(self._unsafe_bulk_solve(requests))
        except Exception as error:
            return [
                JsChallengeProviderResponse(request, None, error)
                for request in requests
            ]

    def _unsafe_bulk_solve(self, requests: list[JsChallengeRequest]) -> Generator[JsChallengeProviderResponse]:
        assert yt_dlp_jsc_deno, 'is_available is false, this should not have been called'

        deno = self._configuration_arg('deno', default=['deno'])[0]
        self.logger.trace(f'Using deno: {deno}')
        cmd = [deno, *self._DENO_ARGS]

        grouped = collections.defaultdict(list)
        for request in requests:
            grouped[request.player_url].append(request)

        with yt_dlp_jsc_deno.path() as path:
            self.logger.trace(f'Using bundle at {path}')
            cmd.append(str(path))

            for player_url, requests in grouped.items():
                try:
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
                except JsChallengeProviderError as error:
                    for request in requests:
                        yield JsChallengeProviderResponse(request, None, error)

    def _call_deno_bundle(
        self,
        /,
        cmd: list[str],
        requests: list[JsChallengeRequest],
        player: str,
        preprocessed: bool,
    ) -> tuple[list[JsChallengeProviderResponse], str | None]:
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
