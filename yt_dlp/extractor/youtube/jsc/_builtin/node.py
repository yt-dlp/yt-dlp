from __future__ import annotations

import re
import shlex
import subprocess

from yt_dlp.extractor.youtube.jsc._builtin.ejs import EJSBaseJCP
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
class NodeJCP(EJSBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'node'
    JS_RUNTIME_NAME = 'node'

    _ARGS = ['-']

    def _run_js_runtime(self, stdin: str, /) -> str:
        args = []

        if self.ejs_setting('jitless', ['false']) != ['false']:
            args.append('--v8-flags=--jitless')

        # Node permission flag changed from experimental to stable in v23.5.0
        if self.runtime_info.version_tuple < (23, 5, 0):
            args.append('--experimental-permission')
            args.append('--no-warnings=ExperimentalWarning')
        else:
            args.append('--permission')

        cmd = [self.runtime_info.path, *args, *self._ARGS]
        self.logger.debug(f'Running node: {shlex.join(cmd)}')
        with Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate_or_kill(stdin)
            stderr = self._clean_stderr(stderr)
            if proc.returncode or stderr:
                msg = f'Error running node process (returncode: {proc.returncode})'
                if stderr:
                    msg = f'{msg}: {stderr.strip()}'
                raise JsChallengeProviderError(msg)

        return stdout

    def _clean_stderr(self, stderr):
        return '\n'.join(
            line for line in stderr.splitlines()
            if not (
                re.match(r'^\[stdin\]:', line)
                or re.match(r'^var jsc', line)
                or '(Use `node --trace-uncaught ...` to show where the exception was thrown)' == line
                or re.match(r'^Node\.js v\d+\.\d+\.\d+$', line)))


@register_preference(NodeJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 900
