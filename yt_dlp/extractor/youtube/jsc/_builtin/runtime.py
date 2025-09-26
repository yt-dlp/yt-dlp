from __future__ import annotations

import collections
import dataclasses
import enum
import functools
import hashlib
import importlib.resources
import json
import sys

import yt_dlp
from yt_dlp.dependencies import yt_dlp_ejs
from yt_dlp.extractor.youtube.jsc._builtin.scripts import load_script
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeProviderRejectedRequest,
    JsChallengeProviderResponse,
    JsChallengeResponse,
    JsChallengeType,
    NChallengeOutput,
    SigChallengeOutput,
)
from yt_dlp.extractor.youtube.pot.provider import provider_bug_report_message
from yt_dlp.utils._jsruntime import JsRuntimeInfo

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Generator

    from yt_dlp.extractor.youtube.jsc.provider import JsChallengeRequest


class ScriptType(enum.Enum):
    LIB = 'lib'
    CORE = 'core'


class ScriptVariant(enum.Enum):
    UNKNOWN = 'unknown'
    MINIFIED = 'minified'
    UNMINIFIED = 'unminified'
    DENO_NPM = 'deno_npm'
    BUN_NPM = 'bun_npm'


class ScriptSource(enum.Enum):
    PYPACKAGE = 'python package'
    BINARY = 'binary'
    CACHE = 'cache'
    WEB = 'web'
    BUILTIN = 'builtin'


@dataclasses.dataclass
class Script:
    type: ScriptType
    variant: ScriptVariant
    source: ScriptSource
    version: str
    code: str

    @functools.cached_property
    def hash(self, /) -> str:
        return hashlib.sha3_512(self.code.encode()).hexdigest()

    def __str__(self, /):
        return f'<Script {self.type.value!r} v{self.version} (source: {self.source.value}) variant={self.variant.value!r} size={len(self.code)} hash={self.hash[:7]}...>'


class JsRuntimeChalBaseJCP(JsChallengeProvider):
    JS_RUNTIME_NAME: str
    _CACHE_SECTION = 'challenge-solver'

    _JCP_GUIDE_URL = 'https://github.com/yt-dlp/yt-dlp/wiki/YouTube-JS-Challenges'
    _REPOSITORY = 'yt-dlp/ejs'
    _SUPPORTED_TYPES = [JsChallengeType.N, JsChallengeType.SIG]
    _SUPPORTED_VERSION = '0.0.1'
    # TODO: insert correct hashes here
    # TODO: Integration tests for each kind of scripts source
    _ALLOWED_HASHES = {
        ScriptType.LIB: {
            ScriptVariant.MINIFIED: 'e11bfeadf92647b462d38a815f1a908ae4d22a0c28ee4a8f761c36ec05bc901780db88b1bd752c07e907d56792478c3e674b4756043c66b3e44f4b9b5956b1ba',
            ScriptVariant.DENO_NPM: '757159fe195bec5228a801e399084e65163b1be0f8c588986bdf775f42295c2c18fdfa0ef70b7e32431b5c6b51342972945daf4ecd92494856fc95d8d62ccd88',
            ScriptVariant.BUN_NPM: '88433fa4318fb092f976b0e904208f810bcdc19adcb3a02deb074886a4fec353aedbd6d0acf7df17135fae51895448878b7d96ce5440b4907cf25adde93c7619',
        },
        ScriptType.CORE: {
            ScriptVariant.MINIFIED: 'ad26b12c8b45577f6048c34b5cbbd43423d0c37bfb453a882053193b78737d781cd80b6eeb1f621394f691c59d878995e0128844c00ee88bf6278c1040baad55',
            ScriptVariant.UNMINIFIED: 'c8d38d6ea4a4552e4815bb46835d7228f48bfc62a778ced96fa981fa98109f9d098835c1d3716c05afe681bdcec372bba33a61ef69fd7173c04dde740c1c7a23',
        },
    }

    _SCRIPT_FILENAMES = {
        ScriptType.LIB: 'lib.js',
        ScriptType.CORE: 'core.js',
    }

    _MIN_SCRIPT_FILENAMES = {
        ScriptType.LIB: 'lib.min.js',
        ScriptType.CORE: 'core.min.js',
    }

    # currently disabled as files are large and we do not support rotation
    _ENABLE_PREPROCESSED_PLAYER_CACHE = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._available = True
        # Note: developer use only, intentionally not documented.
        # This bypasses verification of script hashes and versions.
        # --extractor-args youtubejsc-{provider key}:dev=true
        self.is_dev = self.settings.get('dev', []) == ['true']
        if self.is_dev:
            self.logger.warning(
                f'You have enabled dev mode for {self.PROVIDER_KEY}JCP. '
                f'This is a developer option intended for debugging. \n'
                '         If you experience any issues while using this option, '
                f'{self.ie._downloader._format_err("DO NOT", self.ie._downloader.Styles.ERROR)} open a bug report')

    def _run_js_runtime(self, stdin: str, /) -> str:
        """To be implemented by subclasses"""
        raise NotImplementedError

    def _real_bulk_solve(self, /, requests: list[JsChallengeRequest]):
        grouped: dict[str, list[JsChallengeRequest]] = collections.defaultdict(list)
        for request in requests:
            grouped[request.input.player_url].append(request)

        for player_url, grouped_requests in grouped.items():
            player = None
            if self._ENABLE_PREPROCESSED_PLAYER_CACHE:
                player = self.ie.cache.load(self._CACHE_SECTION, f'player:{player_url}')

            if player:
                cached = True
            else:
                cached = False
                video_id = next((request.video_id for request in grouped_requests), None)
                player = self._get_player(video_id, player_url)

            stdin = self._construct_stdin(player, cached, grouped_requests)
            stdout = self._run_js_runtime(stdin)
            output = json.loads(stdout)
            if output['type'] == 'error':
                raise JsChallengeProviderError(output['error'])

            if self._ENABLE_PREPROCESSED_PLAYER_CACHE and (preprocessed := output.get('preprocessed_player')):
                self.ie.cache.store(self._CACHE_SECTION, f'player:{player_url}', preprocessed)

            for request, response_data in zip(grouped_requests, output['responses']):
                if response_data['type'] == 'error':
                    yield JsChallengeProviderResponse(request, None, response_data['error'])
                else:
                    yield JsChallengeProviderResponse(request, JsChallengeResponse(request.type, (
                        NChallengeOutput(response_data['data']) if request.type is JsChallengeType.N
                        else SigChallengeOutput(response_data['data']))))

    def _construct_stdin(self, player: str, preprocessed: bool, requests: list[JsChallengeRequest], /) -> str:
        json_requests = [{
            'type': request.type.value,
            'challenges': request.input.challenges,
        } for request in requests]
        data = {
            'type': 'preprocessed',
            'preprocessed_player': player,
            'requests': json_requests,
        } if preprocessed else {
            'type': 'player',
            'player': player,
            'requests': json_requests,
            'output_preprocessed': True,
        }
        return f'''\
        {self._lib_script.code}
        Object.assign(globalThis, lib);
        {self._core_script.code}
        console.log(JSON.stringify(jsc({json.dumps(data)})));
        '''

    # region: challenge solver script

    @functools.cached_property
    def _lib_script(self, /):
        return self._get_script(ScriptType.LIB)

    @functools.cached_property
    def _core_script(self, /):
        return self._get_script(ScriptType.CORE)

    def _get_script(self, script_type: ScriptType, /) -> Script:
        for _, from_source in self._iter_script_sources():
            script = from_source(script_type)
            if not script:
                continue
            if not self.is_dev and script.version != self._SUPPORTED_VERSION:
                self.logger.warning(
                    f'Challenge solver {script_type.value} script version {script.version} '
                    f'is not supported (source: {script.source.value}, supported version: {self._SUPPORTED_VERSION})')
            script_hashes = self._ALLOWED_HASHES[script.type].get(script.variant, [])
            if not self.is_dev and script_hashes and script.hash not in script_hashes:
                self.logger.warning(
                    f'Hash mismatch on challenge solver {script.type.value} script '
                    f'(source: {script.source.value}, hash: {script.hash})!{provider_bug_report_message(self)}')
            else:
                self.logger.debug(f'Using challenge solver {script.type.value} script v{script.version} (source: {script.source.value}, variant: {script.variant.value})')
                return script

        self._available = False
        raise JsChallengeProviderRejectedRequest(f'No usable challenge solver {script_type.value} script available')

    def _iter_script_sources(self) -> Generator[tuple[ScriptSource, callable]]:
        yield from [
            (ScriptSource.PYPACKAGE, self._pypackage_source),
            (ScriptSource.BINARY, self._binary_source),
            (ScriptSource.CACHE, self._cached_source),
            (ScriptSource.BUILTIN, self._builtin_source),
            (ScriptSource.WEB, self._web_release_source)]

    def _pypackage_source(self, script_type: ScriptType, /) -> Script | None:
        if not yt_dlp_ejs:
            return None
        code = yt_dlp_ejs.yt_solver_core() if script_type is ScriptType.CORE else yt_dlp_ejs.yt_solver_lib()
        return Script(script_type, ScriptVariant.MINIFIED, ScriptSource.PYPACKAGE, yt_dlp_ejs.version, code)

    def _binary_source(self, script_type: ScriptType, /) -> Script | None:
        if (
            getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
            and importlib.resources.is_resource(yt_dlp, self._MIN_SCRIPT_FILENAMES[script_type])
        ):
            code = importlib.resources.read_text(yt_dlp, self._MIN_SCRIPT_FILENAMES[script_type])
            return Script(script_type, ScriptVariant.MINIFIED, ScriptSource.BINARY, self._SUPPORTED_VERSION, code)
        return None

    def _cached_source(self, script_type: ScriptType, /) -> Script | None:
        if data := self.ie.cache.load(self._CACHE_SECTION, script_type.value):
            return Script(script_type, ScriptVariant.MINIFIED, ScriptSource.CACHE, data['version'], data['code'])
        return None

    def _builtin_source(self, script_type: ScriptType, /) -> Script | None:
        error_hook = lambda _: self.logger.warning(
            f'Failed to read builtin challenge solver {script_type.value} script{provider_bug_report_message(self)}')
        code = load_script(
            self._SCRIPT_FILENAMES[script_type], error_hook=error_hook)
        if code:
            return Script(script_type, ScriptVariant.UNMINIFIED, ScriptSource.BUILTIN, self._SUPPORTED_VERSION, code)
        return None

    def _web_release_source(self, script_type: ScriptType, /) -> Script | None:
        if 'ejs-github' not in self.ie.get_param('download_ext_components', []):
            self._report_ext_component_skipped('ejs-github', 'challenge solver script')
            return None
        url = f'https://github.com/{self._REPOSITORY}/releases/download/{self._SUPPORTED_VERSION}/{self._MIN_SCRIPT_FILENAMES[script_type]}'
        if code := self.ie._download_webpage_with_retries(
            url, None, f'[{self.logger.prefix}] Downloading challenge solver {script_type.value} script from  {url}',
            f'[{self.logger.prefix}] Failed to download challenge solver {script_type.value} script', fatal=False,
        ):
            self.ie.cache.store(self._CACHE_SECTION, script_type.value, {
                'version': self._SUPPORTED_VERSION,
                'code': code,
            })
            return Script(script_type, ScriptVariant.MINIFIED, ScriptSource.WEB, self._SUPPORTED_VERSION, code)
        return None

    # endregion: challenge solver script

    @property
    def runtime_info(self) -> JsRuntimeInfo | bool:
        runtime = self.ie._downloader._js_runtimes.get(self.JS_RUNTIME_NAME)
        if not runtime or not runtime.info or not runtime.info.supported:
            return False
        return runtime.info

    def is_available(self, /) -> bool:
        if not self.runtime_info:
            return False
        return self._available

    def _report_ext_component_skipped(self, component: str, component_description: str):
        self.logger.warning(
            f'External {component_description} downloads are disabled. '
            f'This may be required to solve JS challenges using {self.JS_RUNTIME_NAME} JS runtime. '
            f'You can enable {component_description} downloads with "--download-ext-components {component}". '
            f'For more information and alternatives, refer to  {self._JCP_GUIDE_URL}')
