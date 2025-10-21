from __future__ import annotations

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
from yt_dlp.utils import Popen

# KNOWN ISSUES:
# - If node_modules is present and includes a requested lib, the version we request is ignored
#   and whatever installed in node_modules is used.
# - No way to ignore existing node_modules, lock files, etc.
# - No sandboxing options available
# - Cannot detect if npm packages are cached without potentially downloading them.
#   `--no-install` appears to disable the cache.


@register_provider
class BunJCP(JsRuntimeChalBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'bun'
    JS_RUNTIME_NAME = 'bun'
    BUN_NPM_LIB_FILENAME = 'yt.solver.bun.lib.js'

    def _iter_script_sources(self):
        for source, func in super()._iter_script_sources():
            if source == ScriptSource.WEB:
                # Prioritize GitHub scripts over Bun NPM script as bun NPM auto-install is unreliable.
                yield source, func
                yield ScriptSource.BUILTIN, self._bun_npm_source
            else:
                yield source, func

    def _bun_npm_source(self, script_type: ScriptType, /) -> Script | None:
        if script_type != ScriptType.LIB:
            return None
        if 'ejs:npm' not in self.ie.get_param('remote_components', []):
            self._report_remote_component_skipped('ejs:npm', 'NPM package')
            return None

        # Bun-specific lib scripts that uses Bun autoimport
        # https://bun.com/docs/runtime/autoimport
        error_hook = lambda e: self.logger.warning(
            f'Failed to read bun challenge solver lib script: {e}{provider_bug_report_message(self)}')
        code = load_script(
            self.BUN_NPM_LIB_FILENAME, error_hook=error_hook)
        if code:
            return Script(script_type, ScriptVariant.BUN_NPM, ScriptSource.BUILTIN, self._SCRIPT_VERSION, code)
        return None

    def _run_js_runtime(self, stdin: str, /) -> str:
        # https://bun.com/docs/cli/run
        options = ['--no-addons', '--prefer-offline']
        if self._lib_script.variant == ScriptVariant.BUN_NPM:
            # Enable auto-install even if node_modules is present
            options.append('--install=fallback')
        else:
            options.append('--no-install')
        cmd = [self.runtime_info.path, '--bun', 'run', *options, '-']
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
