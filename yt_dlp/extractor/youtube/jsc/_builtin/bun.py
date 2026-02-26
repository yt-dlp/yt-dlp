from __future__ import annotations

import os
import re
import shlex
import subprocess
import urllib.parse

from yt_dlp.extractor.youtube.jsc._builtin.ejs import (
    _EJS_WIKI_URL,
    EJSBaseJCP,
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
from yt_dlp.utils.networking import HTTPHeaderDict, clean_proxies

# KNOWN ISSUES:
# - If node_modules is present and includes a requested lib, the version we request is ignored
#   and whatever installed in node_modules is used.
# - No way to ignore existing node_modules, lock files, etc.
# - No sandboxing options available
# - Cannot detect if npm packages are cached without potentially downloading them.
#   `--no-install` appears to disable the cache.
# - npm auto-install may fail with an integrity error when using HTTP proxies
# - npm auto-install HTTP proxy support may be limited on older Bun versions
# - Cannot disable the transpiler / specify lang for stdin


@register_provider
class BunJCP(EJSBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'bun'
    JS_RUNTIME_NAME = 'bun'
    BUN_NPM_LIB_FILENAME = 'yt.solver.bun.lib.js'
    SUPPORTED_PROXY_SCHEMES = ['http', 'https']

    def _iter_script_sources(self):
        yield from super()._iter_script_sources()
        yield ScriptSource.BUILTIN, self._bun_npm_source

    def _bun_npm_source(self, script_type: ScriptType, /):
        if script_type != ScriptType.LIB:
            return None
        if 'ejs:npm' not in self.ie.get_param('remote_components', []):
            return self._skip_component('ejs:npm')

        # Check to see if the environment proxies are compatible with Bun npm source
        if unsupported_scheme := self._check_env_proxies(self._get_env_options()):
            self.logger.warning(
                f'Bun NPM package downloads only support HTTP/HTTPS proxies; skipping remote NPM package downloads. '
                f'Provide another distribution of the challenge solver script or use '
                f'another JS runtime that supports "{unsupported_scheme}" proxies. '
                f'For more information and alternatives, refer to  {_EJS_WIKI_URL}')
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

    def _check_env_proxies(self, env):
        # check that the schemes of both HTTP_PROXY and HTTPS_PROXY are supported
        for key in ('HTTP_PROXY', 'HTTPS_PROXY'):
            proxy = env.get(key)
            if not proxy:
                continue
            scheme = urllib.parse.urlparse(proxy).scheme.lower()
            if scheme not in self.SUPPORTED_PROXY_SCHEMES:
                return scheme
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
        if self.ie.get_param('nocheckcertificate'):
            options['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

        # Disable Bun transpiler cache
        options['BUN_RUNTIME_TRANSPILER_CACHE_PATH'] = '0'

        # Prevent segfault: <https://github.com/oven-sh/bun/issues/22901>
        options.pop('JSC_useJIT', None)
        if self.ejs_setting('jitless', ['false']) != ['false']:
            options['BUN_JSC_useJIT'] = '0'

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
            stderr = self._clean_stderr(stderr)
            if proc.returncode or stderr:
                msg = f'Error running bun process (returncode: {proc.returncode})'
                if stderr:
                    msg = f'{msg}: {stderr.strip()}'
                raise JsChallengeProviderError(msg)
        return stdout

    def _clean_stderr(self, stderr):
        return '\n'.join(
            line for line in stderr.splitlines()
            if not re.match(r'^Bun v\d+\.\d+\.\d+ \([\w\s]+\)$', line))


@register_preference(BunJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 800
