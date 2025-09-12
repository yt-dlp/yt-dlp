from __future__ import annotations

import contextlib
import functools
import shlex
import subprocess

from yt_dlp.extractor.youtube.jsc._builtin.bundle import load_bundle_code
from yt_dlp.extractor.youtube.jsc._builtin.runtime import BundleSource, BundleType, JsRuntimeJCPBase, _Bundle
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
class DenoJCP(JsRuntimeJCPBase, BuiltinIEContentProvider):
    PROVIDER_NAME = 'deno'
    JS_RUNTIME_NAME = 'deno'

    _DENO_OPTIONS = ['--no-prompt', '--no-remote']
    _NPM_LIB_BUNDLE_FILENAME = 'deno.lib.js'

    @functools.cache  # noqa: B019
    def _provider_bundle_hook(self, bundle_type: BundleType, /) -> _Bundle | None:
        if bundle_type != BundleType.LIB:
            return None
        # TODO: check that npm downloads are available

        # Deno-specific lib bundle that uses Deno NPM imports
        code = load_bundle_code(
            self._NPM_LIB_BUNDLE_FILENAME,
            error_hook=lambda _: self.logger.warning('Failed to read deno jsc file from source distribution'))
        if code:
            # TODO: any other permissions we want when not using --no-remote?
            with contextlib.suppress(ValueError):
                self._DENO_OPTIONS.remove('--no-remote')
            return _Bundle(bundle_type, BundleSource.BUILTIN, self._SUPPORTED_VERSION, code)
        return None

    def _run_js_runtime(self, stdin: str, /) -> str:
        cmd = [self.runtime_info.path, 'run', *self._DENO_OPTIONS, '-']
        self.logger.trace(f'Running deno: {shlex.join(cmd)}')
        with Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate_or_kill(stdin)
            if proc.returncode or stderr:
                msg = 'Error running deno process'
                if stderr:
                    msg = f'{msg}: {stderr}'
                raise JsChallengeProviderError(msg)

        return stdout


@register_preference(DenoJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 1000
