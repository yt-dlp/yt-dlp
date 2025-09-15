from __future__ import annotations

import shlex
import subprocess

from yt_dlp.extractor.youtube.jsc._builtin.bundle import load_bundle_code
from yt_dlp.extractor.youtube.jsc._builtin.runtime import (
    JsRuntimeChalBaseJCP,
    Script,
    ScriptSource,
    ScriptType,
    ScriptTypeVariant,
)
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeRequest,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.extractor.youtube.pot.provider import provider_bug_report_message
from yt_dlp.utils import Popen


@register_provider
class BunJCP(JsRuntimeChalBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'bun'
    JS_RUNTIME_NAME = 'bun'

    _ARGS = ['--bun', 'run', '-']
    BUN_NPM_LIB_FILENAME = 'bun.lib.js'

    def _iter_script_sources(self):
        for source, func in super()._iter_script_sources():
            if source == ScriptSource.WEB:
                yield ScriptSource.BUILTIN, self._bun_npm_source
            yield source, func

    def _bun_npm_source(self, script_type: ScriptType, /) -> Script | None:
        if script_type != ScriptType.LIB:
            return None
        if 'npm' not in self.ie.get_param('download_ext_components', []):
            self._report_ext_component_skipped('npm', 'NPM package')
            return None

        # Bun-specific lib bundle that uses Bun autoimport
        # https://bun.com/docs/runtime/autoimport
        error_hook = lambda e: self.logger.warning(
            f'Failed to read bun challenge solver lib script: {e}{provider_bug_report_message(self)}')
        code = load_bundle_code(
            self.BUN_NPM_LIB_FILENAME, error_hook=error_hook)
        if code:
            return Script(script_type, ScriptTypeVariant.BUN_NPM, ScriptSource.BUILTIN, self._SUPPORTED_VERSION, code)
        return None

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
