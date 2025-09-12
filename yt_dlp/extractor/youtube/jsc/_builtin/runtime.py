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

# TODO: decouple BundleType from the filename as there can be min and non-min versions


class BundleType(enum.Enum):
    LIB = 'lib'
    JSC = 'jsc'


class BundleSource(enum.Enum):
    PYPACKAGE = 'python package'
    BINARY = 'binary'
    CACHE = 'cache'
    WEB = 'web'
    BUILTIN = 'builtin'


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
            '488c1903d8beb24ee9788400b2a91e724751b04988ba4de398320de0e36b4a9e3a8db58849189bf1d48df3fc4b0972d96b4aabfd80fea25d7c43988b437062fd',
            'cbd33afbfa778e436aef774f3983f0b1234ad7f737ea9dbd9783ee26dce195f4b3242d1e202b2038e748044960bc2f976372e883c76157b24acdea939dba7603',
        ],
        BundleType.JSC: [
            'df0c08c152911dedd35a98bbbb6a1786718c11e4233c52abda3d19fd11d97c3ba09745dfbca913ddeed72fead18819f62139220420c41a04d5a66ed629fbde4e',
            '8abfd4818573b6cf397cfae227661e3449fb5ac737a272ac0cf8268d94447b04b1c9a15f459b336175bf0605678a376e962df99b2c8d5498f16db801735f771c',
        ],
    }

    _BUNDLE_FILENAMES = {
        BundleType.LIB: 'lib.js',
        BundleType.JSC: 'jsc.js',
    }

    _MIN_BUNDLE_FILENAMES = {
        BundleType.LIB: 'lib.min.js',
        BundleType.JSC: 'jsc.min.js',
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
                self.logger.warning(f'Hash mismatch on {bundle.type.value} (source: {bundle.source.value}, hash: {bundle.hash})!')

            else:
                self.logger.debug(f'Using {bundle.type.value} v{bundle.version} (source: {bundle.source.value})')
                return bundle

        self._available = False
        raise JsChallengeProviderError(f'failed to find usable {bundle_type.value}')

    def _iter_bundles(self, bundle_type: BundleType, /) -> Generator[_Bundle]:
        # TODO: consider bun/deno npm resolver bundles?
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
            and importlib.resources.is_resource(yt_dlp, self._MIN_BUNDLE_FILENAMES[bundle_type])
        ):
            code = importlib.resources.read_text(yt_dlp, self._MIN_BUNDLE_FILENAMES[bundle_type])
            yield _Bundle(bundle_type, BundleSource.BINARY, self._SUPPORTED_VERSION, code)

        if data := self.ie.cache.load(self._CACHE_SECTION, bundle_type.value):
            yield _Bundle(bundle_type, BundleSource.CACHE, data['version'], data['code'])

        # Check if included in source distribution
        code = load_bundle_code(
            self._BUNDLE_FILENAMES[bundle_type],
            error_hook=lambda _: self.logger.warning('Failed to read bundled jsc file from source distribution'))
        if code:
            yield _Bundle(bundle_type, BundleSource.BUILTIN, self._SUPPORTED_VERSION, code)

        # Try provider bundle method
        if bundle := self._provider_bundle_hook(bundle_type):
            self.logger.trace('fetched bundle from provider hook')
            yield bundle

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

    def _provider_bundle_hook(self, bundle_type: BundleType, /) -> _Bundle | None:
        """To be implemented by providers"""
        return None

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
