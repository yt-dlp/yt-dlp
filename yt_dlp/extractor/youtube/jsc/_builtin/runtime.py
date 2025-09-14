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
from yt_dlp.extractor.youtube.jsc._builtin.bundle import load_bundle_code
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


class ScriptTypeVariant(enum.Enum):
    UNKNOWN = 'unknown'
    MINIFIED = 'minified'
    UNMINIFIED = 'unminified'
    DENO_NPM = 'deno_npm'


class ScriptSource(enum.Enum):
    PYPACKAGE = 'python package'
    BINARY = 'binary'
    CACHE = 'cache'
    WEB = 'web'
    BUILTIN = 'builtin'


@dataclasses.dataclass
class Script:
    type: ScriptType
    variant: ScriptTypeVariant
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

    _REPOSITORY = 'yt-dlp/yt-dlp-jsc-deno'
    _SUPPORTED_TYPES = [JsChallengeType.N, JsChallengeType.SIG]
    _SUPPORTED_VERSION = '0.0.1'
    # TODO: insert correct hashes here
    # TODO: Integration tests for each kind of bundle source
    _ALLOWED_HASHES = {
        ScriptType.LIB: [
            '488c1903d8beb24ee9788400b2a91e724751b04988ba4de398320de0e36b4a9e3a8db58849189bf1d48df3fc4b0972d96b4aabfd80fea25d7c43988b437062fd',
            'cbd33afbfa778e436aef774f3983f0b1234ad7f737ea9dbd9783ee26dce195f4b3242d1e202b2038e748044960bc2f976372e883c76157b24acdea939dba7603',
        ],
        ScriptType.CORE: [
            'df0c08c152911dedd35a98bbbb6a1786718c11e4233c52abda3d19fd11d97c3ba09745dfbca913ddeed72fead18819f62139220420c41a04d5a66ed629fbde4e',
            '8abfd4818573b6cf397cfae227661e3449fb5ac737a272ac0cf8268d94447b04b1c9a15f459b336175bf0605678a376e962df99b2c8d5498f16db801735f771c',
        ],
    }

    _SCRIPT_FILENAMES = {
        ScriptType.LIB: 'lib.js',
        ScriptType.CORE: 'core.js',
    }

    _MIN_SCRIPT_FILENAMES = {
        ScriptType.LIB: 'lib.min.js',
        ScriptType.CORE: 'core.min.js',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dev_mode = self.settings.get('dev_mode', []) == ['true']
        self._available = True

    def _run_js_runtime(self, stdin: str, /) -> str:
        """To be implemented by subclasses"""
        raise NotImplementedError

    def _real_bulk_solve(self, /, requests: list[JsChallengeRequest]):
        grouped: dict[str, list[JsChallengeRequest]] = collections.defaultdict(list)
        for request in requests:
            grouped[request.input.player_url].append(request)

        for player_url, grouped_requests in grouped.items():

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

            if preprocessed := output.get('preprocessed_player'):
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
            # TODO: i despise nsig name
            'type': 'nsig' if request.type.value == 'n' else request.type.value,
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
        const {{ astring, meriyah }} = lib;
        {self._core_script.code}
        console.log(JSON.stringify(jsc({json.dumps(data)})));
        '''

    # region: challenge solver script

    @functools.cached_property
    def _lib_script(self, /):
        return self._get_bundle(ScriptType.LIB)

    @functools.cached_property
    def _core_script(self, /):
        return self._get_bundle(ScriptType.CORE)

    def _get_bundle(self, bundle_type: ScriptType, /) -> Script:
        for bundle in self._iter_script_sources(bundle_type):
            if bundle.version != self._SUPPORTED_VERSION:
                self.logger.warning(
                    f'Challenge solver {bundle_type.value} script version {bundle.version} '
                    f'is not supported (source: {bundle.source.value}, supported version: {self._SUPPORTED_VERSION})')
                if not self.dev_mode:
                    continue
            elif bundle.hash not in self._ALLOWED_HASHES[bundle.type] and not self.dev_mode:
                self.logger.warning(
                    f'Hash mismatch on challenge solver {bundle.type.value} script '
                    f'(source: {bundle.source.value}, hash: {bundle.hash})!{provider_bug_report_message(self)}')
            else:
                self.logger.debug(f'Using challenge solver {bundle.type.value} script v{bundle.version} (source: {bundle.source.value}, variant: {bundle.variant.value})')
                return bundle

        self._available = False
        raise JsChallengeProviderRejectedRequest(f'No usable challenge solver {bundle_type.value} script available')

    def _iter_script_sources(self, script_type: ScriptType, /) -> Generator[Script]:
        for getter in (
            self._pypackage_source,
            self._binary_source,
            self._cached_source,
            self._builtin_source,
            self._provider_hook_source,
            self._web_release_source,
        ):
            # TODO: fix typing
            script = getter(script_type)
            if script:
                yield script

    def _pypackage_source(self, script_type: ScriptType, /) -> Script | None:
        try:
            import yt_dlp_jsc as yt_dlp_ejs
        except ImportError as e:
            self.logger.trace(f'yt_dlp_ejs python package unavailable, reason: {e}')
            return None
        # TODO: fix API naming
        code = yt_dlp_ejs.jsc() if script_type is ScriptType.CORE else yt_dlp_ejs.lib()
        return Script(script_type, ScriptTypeVariant.MINIFIED, ScriptSource.PYPACKAGE, yt_dlp_ejs.version, code)

    def _binary_source(self, script_type: ScriptType, /) -> Script | None:
        if (
            # Use bundled JavaScript only in release binaries
            getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
            and importlib.resources.is_resource(yt_dlp, self._MIN_SCRIPT_FILENAMES[script_type])
        ):
            code = importlib.resources.read_text(yt_dlp, self._MIN_SCRIPT_FILENAMES[script_type])
            return Script(script_type, ScriptTypeVariant.MINIFIED, ScriptSource.BINARY, self._SUPPORTED_VERSION, code)
        return None

    def _cached_source(self, script_type: ScriptType, /) -> Script | None:
        if data := self.ie.cache.load(self._CACHE_SECTION, script_type.value):
            return Script(script_type, ScriptTypeVariant.MINIFIED, ScriptSource.CACHE, data['version'], data['code'])
        return None

    def _builtin_source(self, script_type: ScriptType, /) -> Script | None:
        error_hook = lambda _: self.logger.warning(
            f'Failed to read builtin challenge solver {script_type.value} script{provider_bug_report_message(self)}')
        code = load_bundle_code(
            self._SCRIPT_FILENAMES[script_type], error_hook=error_hook)
        if code:
            return Script(script_type, ScriptTypeVariant.UNMINIFIED, ScriptSource.BUILTIN, self._SUPPORTED_VERSION, code)
        return None

    def _provider_hook_source(self, script_type: ScriptType, /) -> Script | None:
        if bundle := self._script_provider_hook(script_type):
            self.logger.trace(f'Using challenge solver {script_type.value} script from provider hook')
            return bundle
        return None

    def _script_provider_hook(self, script_type: ScriptType, /) -> Script | None:
        """Optional additional source for scripts, to be implemented by providers"""
        return None

    def _web_release_source(self, script_type: ScriptType, /) -> Script | None:
        # TODO: check if github downloads are enabled
        url = f'https://github.com/{self._REPOSITORY}/releases/download/{self._SUPPORTED_VERSION}/{self._MIN_SCRIPT_FILENAMES[script_type]}'
        if code := self.ie._download_webpage(
            url, None, f'Downloading challenge solver {script_type.value} script from  {url}',
            f'Failed to download challenge solver {script_type.value} script', fatal=False,
        ):
            self.ie.cache.store(self._CACHE_SECTION, script_type.value, {
                'version': self._SUPPORTED_VERSION,
                'code': code,
            })
            return Script(script_type, ScriptTypeVariant.MINIFIED, ScriptSource.WEB, self._SUPPORTED_VERSION, code)
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
