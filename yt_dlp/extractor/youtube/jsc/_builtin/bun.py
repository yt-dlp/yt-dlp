from __future__ import annotations

import shlex
import subprocess

from yt_dlp.extractor.youtube.jsc._builtin.runtime import JsRuntimeChalBaseJCP
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeRequest,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.utils import Popen


@register_provider
class BunJCP(JsRuntimeChalBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'bun'
    JS_RUNTIME_NAME = 'bun'

    _ARGS = ['--bun', 'run', '-']

    # TODO: bun npm script hook

    def _run_js_runtime(self, stdin: str, /) -> str:
        cmd = [self.runtime_info.path, *self._ARGS]
        self.logger.debug(f'Running bun: {shlex.join(cmd)}')
        with Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate_or_kill(stdin)
            if proc.returncode or stderr:
                msg = 'Error running bun process'
                if stderr:
                    msg = f'{msg}: {stderr}'
                raise JsChallengeProviderError(msg)

        return stdout


@register_preference(BunJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 800
