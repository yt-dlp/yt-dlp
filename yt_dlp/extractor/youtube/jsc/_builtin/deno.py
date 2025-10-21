from __future__ import annotations

import re
import shlex
import subprocess

from yt_dlp.extractor.youtube.jsc._builtin.runtime import (
    JsRuntimeChalBaseJCP,
    Script,
    ScriptSource,
    ScriptType,
    ScriptVariant,
)
from yt_dlp.extractor.youtube.jsc._builtin.vendor import load_script
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeRequest,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.extractor.youtube.pot.provider import provider_bug_report_message
from yt_dlp.utils import Popen, remove_terminal_sequences


@register_provider
class DenoJCP(JsRuntimeChalBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'deno'
    JS_RUNTIME_NAME = 'deno'

    _DENO_BASE_OPTIONS = ['--no-prompt', '--no-remote', '--no-lock', '--node-modules-dir=none', '--no-config']
    DENO_NPM_LIB_FILENAME = 'yt.solver.deno.lib.js'
    _NPM_PACKAGES_CACHED = False

    def _iter_script_sources(self):
        for source, func in super()._iter_script_sources():
            if source == ScriptSource.WEB:
                yield ScriptSource.BUILTIN, self._deno_npm_source
            yield source, func

    def _deno_npm_source(self, script_type: ScriptType, /) -> Script | None:
        if script_type != ScriptType.LIB:
            return None
        # Deno-specific lib scripts that uses Deno NPM imports
        error_hook = lambda e: self.logger.warning(
            f'Failed to read deno challenge solver lib script: {e}{provider_bug_report_message(self)}')
        code = load_script(
            self.DENO_NPM_LIB_FILENAME, error_hook=error_hook)
        if not code:
            return None
        if 'ejs:npm' not in self.ie.get_param('remote_components', []):
            # We may still be able to continue if the npm packages are available/cached
            self._NPM_PACKAGES_CACHED = self._npm_packages_cached(code)
            if not self._NPM_PACKAGES_CACHED:
                self._report_remote_component_skipped('ejs:npm', 'NPM package')
                return None
        return Script(script_type, ScriptVariant.DENO_NPM, ScriptSource.BUILTIN, self._SCRIPT_VERSION, code)

    def _npm_packages_cached(self, stdin: str) -> bool:
        # Check if npm packages are cached, so we can run without --remote-components ejs:npm
        self.logger.debug('Checking if npm packages are cached')
        try:
            self._run_deno(stdin, [*self._DENO_BASE_OPTIONS, '--cached-only'])
        except JsChallengeProviderError as e:
            self.logger.trace(f'Deno npm packages not cached: {e}')
            return False
        return True

    def _run_js_runtime(self, stdin: str, /) -> str:
        options = [*self._DENO_BASE_OPTIONS]
        if self._lib_script.variant == ScriptVariant.DENO_NPM and self._NPM_PACKAGES_CACHED:
            options.append('--cached-only')
        elif self._lib_script.variant != ScriptVariant.DENO_NPM:
            options.append('--no-npm')
            options.append('--cached-only')
        return self._run_deno(stdin, options)

    def _run_deno(self, stdin, options) -> str:
        cmd = [self.runtime_info.path, 'run', *options, '-']
        self.logger.debug(f'Running deno: {shlex.join(cmd)}')
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
                msg = f'Error running deno process (returncode: {proc.returncode})'
                if stderr:
                    msg = f'{msg}: {stderr}'
                raise JsChallengeProviderError(msg)
        return stdout

    def _clean_stderr(self, stderr):
        return '\n'.join(
            line for line in stderr.splitlines()
            if not re.match(r'^Download\s+https\S+$', remove_terminal_sequences(line))
        )


@register_preference(DenoJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 1000
