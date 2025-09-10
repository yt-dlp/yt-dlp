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
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeProviderResponse,
    JsChallengeResponse,
    JsChallengeType,
    NSigChallengeOutput,
    SigChallengeOutput,
)
from yt_dlp.utils._jsruntime import JsRuntimeInfo

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Generator

    from yt_dlp.extractor.youtube.jsc.provider import JsChallengeRequest


class BundleType(enum.Enum):
    LIB = 'lib.min.js'
    JSC = 'jsc.min.js'


class BundleSource(enum.Enum):
    PYPACKAGE = 'python package'
    BINARY = 'binary'
    CACHE = 'cache'
    WEB = 'web'


@dataclasses.dataclass
class _Bundle:
    type: BundleType
    source: BundleSource
    version: str
    code: str

    @functools.cached_property
    def hash(self, /) -> str:
        return hashlib.sha3_512(self.code.encode()).hexdigest()

    def __str__(self, /):
        return f'<JSCBundle {self.type.value!r} v{self.version} (source: {self.source.value}) size={len(self.code)} hash={self.hash[:7]}...>'


class JsRuntimeJCPBase(JsChallengeProvider):
    JS_RUNTIME_NAME: str
    _CACHE_SECTION = 'jsc-builtin'

    _REPOSITORY = 'yt-dlp/yt-dlp-jsc-deno'
    _SUPPORTED_TYPES = [JsChallengeType.NSIG, JsChallengeType.SIG]
    _SUPPORTED_VERSION = '0.0.1'
    # TODO: insert correct hashes here
    _ALLOWED_HASHES = {
        BundleType.LIB: [
            'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26',
            'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26',
        ],
        BundleType.JSC: [
            'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26',
            'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26',
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._debug = self.settings.get('debug', []) == ['true']
        self._available = True

    def _run_js_runtime(self, stdin: str, /) -> str:
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
                        NSigChallengeOutput(response_data['data']) if request.type is JsChallengeType.NSIG
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
        {self._lib_bundle.code}
        const {{ astring, meriyah }} = lib;
        {self._jsc_bundle.code}
        console.log(JSON.stringify(jsc({json.dumps(data)})));
        '''

    @functools.cached_property
    def _lib_bundle(self, /):
        return self._get_bundle(BundleType.LIB)

    @functools.cached_property
    def _jsc_bundle(self, /):
        return self._get_bundle(BundleType.JSC)

    def _get_bundle(self, bundle_type: BundleType, /) -> _Bundle:
        for bundle in self._iter_bundles(bundle_type):
            if bundle.version != self._SUPPORTED_VERSION:
                self.logger.debug(f'Version {bundle.version} ({bundle.type.value} (source: {bundle.source.value}) is not supported')

            elif bundle.hash not in self._ALLOWED_HASHES[bundle.type] and not self._debug:
                self.logger.warning(f'Hash mismatch on {bundle.type.value} (source: {bundle.source.value})!')

            else:
                self.logger.debug(f'Using {bundle.type.value} v{bundle.version} (source: {bundle.source.value})')
                return bundle

        self._available = False
        raise JsChallengeProviderError(f'failed to find usable {bundle_type.value}')

    def _iter_bundles(self, bundle_type: BundleType, /) -> Generator[_Bundle]:
        try:
            import yt_dlp_jsc
        except ImportError:
            if self._debug:
                self.logger.warning('Failed to import yt_dlp_jsc package in debug mode')
        else:
            code = yt_dlp_jsc.jsc() if bundle_type is BundleType.JSC else yt_dlp_jsc.lib()
            yield _Bundle(bundle_type, BundleSource.PYPACKAGE, yt_dlp_jsc.version, code)

        if (
            # Use bundled JavaScript only in release binaries
            getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
            and importlib.resources.is_resource(yt_dlp, bundle_type.value)
        ):
            code = importlib.resources.read_text(yt_dlp, bundle_type.value)
            yield _Bundle(bundle_type, BundleSource.BINARY, self._SUPPORTED_VERSION, code)

        if data := self.ie.cache.load(self._CACHE_SECTION, bundle_type.value):
            yield _Bundle(bundle_type, BundleSource.CACHE, data['version'], data['code'])

        if code := self.ie._download_webpage(
            f'https://github.com/{self._REPOSITORY}/releases/download/{self._SUPPORTED_VERSION}/{bundle_type.value}',
            None, f'Downloading supplementary {bundle_type.value} file',
            f'Failed to download supplementary {bundle_type.value} file', fatal=False,
        ):
            self.ie.cache.store(self._CACHE_SECTION, bundle_type.value, {
                'version': self._SUPPORTED_VERSION,
                'code': code,
            })
            yield _Bundle(bundle_type, BundleSource.WEB, self._SUPPORTED_VERSION, code)

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
