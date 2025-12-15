from __future__ import annotations

import collections
import dataclasses
import enum
import functools
import hashlib
import json

from yt_dlp.dependencies import yt_dlp_ejs as _has_ejs
from yt_dlp.extractor.youtube.jsc._builtin import vendor
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
from yt_dlp.extractor.youtube.pot._provider import configuration_arg
from yt_dlp.extractor.youtube.pot.provider import provider_bug_report_message
from yt_dlp.utils import version_tuple
from yt_dlp.utils._jsruntime import JsRuntimeInfo

if _has_ejs:
    import yt_dlp_ejs.yt.solver

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from yt_dlp.extractor.youtube.jsc.provider import JsChallengeRequest

_EJS_WIKI_URL = 'https://github.com/yt-dlp/yt-dlp/wiki/EJS'


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
    PYPACKAGE = 'python package'  # PyPI, PyInstaller exe, zipimport binary, etc
    CACHE = 'cache'  # GitHub release assets (cached)
    WEB = 'web'  # GitHub release assets (downloaded)
    BUILTIN = 'builtin'  # vendored (full core script; import-only lib script + NPM cache)


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


class EJSBaseJCP(JsChallengeProvider):
    JS_RUNTIME_NAME: str
    _CACHE_SECTION = 'challenge-solver'

    _REPOSITORY = 'yt-dlp/ejs'
    _SUPPORTED_TYPES = [JsChallengeType.N, JsChallengeType.SIG]
    _SCRIPT_VERSION = vendor.VERSION
    # TODO: Integration tests for each kind of scripts source
    _ALLOWED_HASHES = {
        ScriptType.LIB: {
            ScriptVariant.UNMINIFIED: vendor.HASHES['yt.solver.lib.js'],
            ScriptVariant.MINIFIED: vendor.HASHES['yt.solver.lib.min.js'],
            ScriptVariant.DENO_NPM: vendor.HASHES['yt.solver.deno.lib.js'],
            ScriptVariant.BUN_NPM: vendor.HASHES['yt.solver.bun.lib.js'],
        },
        ScriptType.CORE: {
            ScriptVariant.MINIFIED: vendor.HASHES['yt.solver.core.min.js'],
            ScriptVariant.UNMINIFIED: vendor.HASHES['yt.solver.core.js'],
        },
    }

    _SCRIPT_FILENAMES = {
        ScriptType.LIB: 'yt.solver.lib.js',
        ScriptType.CORE: 'yt.solver.core.js',
    }

    _MIN_SCRIPT_FILENAMES = {
        ScriptType.LIB: 'yt.solver.lib.min.js',
        ScriptType.CORE: 'yt.solver.core.min.js',
    }

    # currently disabled as files are large and we do not support rotation
    _ENABLE_PREPROCESSED_PLAYER_CACHE = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._available = True
        self.ejs_settings = self.ie.get_param('extractor_args', {}).get('youtube-ejs', {})

        # Note: The following 3 args are for developer use only & intentionally not documented.
        # - dev: bypasses verification of script hashes and versions.
        # - repo: use a custom GitHub repository to fetch web script from.
        # - script_version: use a custom script version.
        # E.g. --extractor-args "youtube-ejs:dev=true;script_version=0.1.4"

        self.is_dev = self.ejs_setting('dev', ['false'])[0] == 'true'
        if self.is_dev:
            self.report_dev_option('You have enabled dev mode for EJS JCP Providers.')

        custom_repo = self.ejs_setting('repo', [None])[0]
        if custom_repo:
            self.report_dev_option(f'You have set a custom GitHub repository for EJS JCP Providers ({custom_repo}).')
            self._REPOSITORY = custom_repo

        custom_version = self.ejs_setting('script_version', [None])[0]
        if custom_version:
            self.report_dev_option(f'You have set a custom EJS script version for EJS JCP Providers ({custom_version}).')
            self._SCRIPT_VERSION = custom_version

    def ejs_setting(self, key, *args, **kwargs):
        return configuration_arg(self.ejs_settings, key, *args, **kwargs)

    def report_dev_option(self, message: str):
        self.ie.report_warning(
            f'{message} '
            f'This is a developer option intended for debugging. \n'
            '         If you experience any issues while using this option, '
            f'{self.ie._downloader._format_err("DO NOT", self.ie._downloader.Styles.ERROR)} open a bug report', only_once=True)

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

            # NB: This output belongs after the player request
            self.logger.info(f'Solving JS challenges using {self.JS_RUNTIME_NAME}')

            stdin = self._construct_stdin(player, cached, grouped_requests)
            stdout = self._run_js_runtime(stdin)
            output = json.loads(stdout)
            if output['type'] == 'error':
                raise JsChallengeProviderError(output['error'])

            if self._ENABLE_PREPROCESSED_PLAYER_CACHE and (preprocessed := output.get('preprocessed_player')):
                self.ie.cache.store(self._CACHE_SECTION, f'player:{player_url}', preprocessed)

            for request, response_data in zip(grouped_requests, output['responses'], strict=True):
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
        skipped_components: list[_SkippedComponent] = []
        for _, from_source in self._iter_script_sources():
            script = from_source(script_type)
            if not script:
                continue
            if isinstance(script, _SkippedComponent):
                skipped_components.append(script)
                continue
            if not self.is_dev:
                # Matching patch version is expected to have same hash
                if version_tuple(script.version, lenient=True)[:2] != version_tuple(self._SCRIPT_VERSION, lenient=True)[:2]:
                    self.logger.warning(
                        f'Challenge solver {script_type.value} script version {script.version} '
                        f'is not supported (source: {script.source.value}, variant: {script.variant}, supported version: {self._SCRIPT_VERSION})')
                    if script.source is ScriptSource.CACHE:
                        self.logger.debug('Clearing outdated cached script')
                        self.ie.cache.store(self._CACHE_SECTION, script_type.value, None)
                    continue
                script_hashes = self._ALLOWED_HASHES[script.type].get(script.variant, [])
                if script_hashes and script.hash not in script_hashes:
                    self.logger.warning(
                        f'Hash mismatch on challenge solver {script.type.value} script '
                        f'(source: {script.source.value}, variant: {script.variant}, hash: {script.hash})!{provider_bug_report_message(self)}')
                    if script.source is ScriptSource.CACHE:
                        self.logger.debug('Clearing invalid cached script')
                        self.ie.cache.store(self._CACHE_SECTION, script_type.value, None)
                    continue
            self.logger.debug(
                f'Using challenge solver {script.type.value} script v{script.version} '
                f'(source: {script.source.value}, variant: {script.variant.value})')
            break

        else:
            self._available = False
            raise JsChallengeProviderRejectedRequest(
                f'No usable challenge solver {script_type.value} script available',
                _skipped_components=skipped_components or None,
            )

        return script

    def _iter_script_sources(self) -> Generator[tuple[ScriptSource, Callable[[ScriptType], Script | None]]]:
        yield from [
            (ScriptSource.PYPACKAGE, self._pypackage_source),
            (ScriptSource.CACHE, self._cached_source),
            (ScriptSource.BUILTIN, self._builtin_source),
            (ScriptSource.WEB, self._web_release_source)]

    def _pypackage_source(self, script_type: ScriptType, /) -> Script | None:
        if not _has_ejs:
            return None
        try:
            code = yt_dlp_ejs.yt.solver.core() if script_type is ScriptType.CORE else yt_dlp_ejs.yt.solver.lib()
        except Exception as e:
            self.logger.warning(
                f'Failed to load challenge solver {script_type.value} script from python package: {e}{provider_bug_report_message(self)}')
            return None
        return Script(script_type, ScriptVariant.MINIFIED, ScriptSource.PYPACKAGE, yt_dlp_ejs.version, code)

    def _cached_source(self, script_type: ScriptType, /) -> Script | None:
        if data := self.ie.cache.load(self._CACHE_SECTION, script_type.value):
            return Script(script_type, ScriptVariant(data['variant']), ScriptSource.CACHE, data['version'], data['code'])
        return None

    def _builtin_source(self, script_type: ScriptType, /) -> Script | None:
        error_hook = lambda _: self.logger.warning(
            f'Failed to read builtin challenge solver {script_type.value} script{provider_bug_report_message(self)}')
        code = vendor.load_script(
            self._SCRIPT_FILENAMES[script_type], error_hook=error_hook)
        if code:
            return Script(script_type, ScriptVariant.UNMINIFIED, ScriptSource.BUILTIN, self._SCRIPT_VERSION, code)
        return None

    def _web_release_source(self, script_type: ScriptType, /):
        if 'ejs:github' not in (self.ie.get_param('remote_components') or ()):
            return self._skip_component('ejs:github')
        url = f'https://github.com/{self._REPOSITORY}/releases/download/{self._SCRIPT_VERSION}/{self._MIN_SCRIPT_FILENAMES[script_type]}'
        if code := self.ie._download_webpage_with_retries(
            url, None, f'[{self.logger.prefix}] Downloading challenge solver {script_type.value} script from  {url}',
            f'[{self.logger.prefix}] Failed to download challenge solver {script_type.value} script', fatal=False,
        ):
            self.ie.cache.store(self._CACHE_SECTION, script_type.value, {
                'version': self._SCRIPT_VERSION,
                'variant': ScriptVariant.MINIFIED.value,
                'code': code,
            })
            return Script(script_type, ScriptVariant.MINIFIED, ScriptSource.WEB, self._SCRIPT_VERSION, code)
        return None

    # endregion: challenge solver script

    @property
    def runtime_info(self) -> JsRuntimeInfo | None:
        runtime = self.ie._downloader._js_runtimes.get(self.JS_RUNTIME_NAME)
        if not runtime or not runtime.info or not runtime.info.supported:
            return None
        return runtime.info

    def is_available(self, /) -> bool:
        if not self.runtime_info:
            return False
        return self._available

    def _skip_component(self, component: str, /):
        return _SkippedComponent(component, self.JS_RUNTIME_NAME)


@dataclasses.dataclass
class _SkippedComponent:
    component: str
    runtime: str
