from __future__ import annotations

import os
import shlex
import subprocess
import urllib.parse

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
    JsChallengeProviderRejectedRequest,
    JsChallengeRequest,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.extractor.youtube.pot.provider import provider_bug_report_message
from yt_dlp.utils import Popen
from yt_dlp.utils.networking import HTTPHeaderDict, clean_proxies

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
    SUPPORTED_PROXY_SCHEMES = ['http', 'https']

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

    def _get_env_options(self) -> dict[str, str]:
        options = os.environ.copy()  # pass through existing bun env vars
        request_proxies = self.ie._downloader.proxies.copy()
        clean_proxies(request_proxies, HTTPHeaderDict())

        # Apply 'all' proxy first, then allow per-scheme overrides
        if request_proxies.get('all') is not None:
            options['HTTP_PROXY'] = options['HTTPS_PROXY'] = request_proxies['all']
        for key, env in (('http', 'HTTP_PROXY'), ('https', 'HTTPS_PROXY')):
            val = request_proxies.get(key)
            if val is not None:
                options[env] = val

        # check that the schemes of both HTTP_PROXY and HTTPS_PROXY are supported
        for env in ('HTTP_PROXY', 'HTTPS_PROXY'):
            proxy = options.get(env)
            if not proxy:
                continue
            scheme = urllib.parse.urlparse(proxy).scheme.lower()
            if scheme not in self.SUPPORTED_PROXY_SCHEMES:
                scheme = urllib.parse.urlparse(proxy).scheme.lower()
                self.logger.warning(
                    f'Bun NPM requests only support HTTP/HTTPS proxies; skipping provider. '
                    f'Provide another distribution of the challenge solver script or use '
                    f'another JS runtime that supports "{scheme}" proxies (e.g. deno). '
                    f'For more information, refer to  {self.ie._EJS_WIKI_URL}')
                raise JsChallengeProviderRejectedRequest(
                    f'External requests by "{self.PROVIDER_NAME}" provider do not '
                    f'support proxy scheme "{scheme}". Supported proxy schemes: '
                    f'{", ".join(self.SUPPORTED_PROXY_SCHEMES)}.')
        if self.ie.get_param('nocheckcertificate'):
            options['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
        return options

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
            env=self._get_env_options(),
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
