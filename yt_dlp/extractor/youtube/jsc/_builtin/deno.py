from __future__ import annotations

import contextlib
import shlex
import subprocess

from yt_dlp.extractor.youtube.jsc._builtin.runtime import (
    JsRuntimeChalBaseJCP,
    Script,
    ScriptSource,
    ScriptType,
    ScriptVariant,
)
from yt_dlp.extractor.youtube.jsc._builtin.scripts import load_script
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
class DenoJCP(JsRuntimeChalBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'deno'
    JS_RUNTIME_NAME = 'deno'

    _DENO_OPTIONS = ['--no-prompt', '--no-remote']
    DENO_NPM_LIB_FILENAME = 'yt.solver.deno.lib.js'

    def _iter_script_sources(self):
        for source, func in super()._iter_script_sources():
            if source == ScriptSource.WEB:
                yield ScriptSource.BUILTIN, self._deno_npm_source
            yield source, func

    def _deno_npm_source(self, script_type: ScriptType, /) -> Script | None:
        if script_type != ScriptType.LIB:
            return None
        if 'npm' not in self.ie.get_param('download_ext_components', []):
            self._report_ext_component_skipped('npm', 'NPM package')
            return None
        # Deno-specific lib scripts that uses Deno NPM imports
        error_hook = lambda e: self.logger.warning(
            f'Failed to read deno challenge solver lib script: {e}{provider_bug_report_message(self)}')
        code = load_script(
            self.DENO_NPM_LIB_FILENAME, error_hook=error_hook)
        if code:
            # TODO: any other permissions we want when not using --no-remote?
            with contextlib.suppress(ValueError):
                self._DENO_OPTIONS.remove('--no-remote')
            return Script(script_type, ScriptVariant.DENO_NPM, ScriptSource.BUILTIN, self._SUPPORTED_VERSION, code)
        return None

    def _run_js_runtime(self, stdin: str, /) -> str:
        cmd = [self.runtime_info.path, 'run', *self._DENO_OPTIONS, '-']
        self.logger.debug(f'Running deno: {shlex.join(cmd)}')
        with Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate_or_kill(stdin)
            # TODO: fails when deno needs to download dependencies?
            if proc.returncode or stderr:
                msg = 'Error running deno process'
                if stderr:
                    msg = f'{msg}: {stderr}'
                raise JsChallengeProviderError(msg)

        return stdout


@register_preference(DenoJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 1000
