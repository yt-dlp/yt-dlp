from __future__ import annotations

import collections
import contextlib
import functools
import hashlib
import importlib.resources
import json
import pathlib
import subprocess
import sys
import tempfile

import yt_dlp.version
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeProviderResponse,
    JsChallengeRequest,
    JsChallengeResponse,
    JsChallengeType,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.utils import Popen

TYPE_CHECKING = False
if TYPE_CHECKING:
    import typing
    from collections.abc import Callable, Generator


class _Bundle:
    def __init__(self, path: Callable[[], typing.ContextManager[pathlib.Path]], version: str):
        self._path = path
        self.version = version

    def path(self, /):
        return self._path()

    @property
    def hash(self, /) -> str:
        return self._hash()

    def _hash(self, path: pathlib.Path | None = None, /) -> str:
        if self._hash_digest:
            return self._hash_digest
        with contextlib.ExitStack() as stack:
            if not path:
                path = stack.enter_context(self.path())
            self._hash_digest = _hash_file(path, hashlib.sha3_512)

        return self._hash_digest

    def __str__(self, /):
        with self.path() as path:
            return f'<JSCDenoBundle: version={self.version!r}, hash={self._hash(path)}, path={str(path)!r}>'


def _hash_file(path: pathlib.Path, hash_algorithm: Callable[[], hashlib._Hash]) -> str:
    hasher = hash_algorithm()
    buffer = memoryview(bytearray(256 << 10))

    size = None
    with path.open('rb', buffering=0) as file:
        while size := file.readinto(buffer):
            hasher.update(buffer[:size])
    if size is None:
        raise BlockingIOError('I/O would block')

    return hasher.hexdigest()


@register_provider
class DenoJCP(JsChallengeProvider, BuiltinIEContentProvider):
    PROVIDER_NAME = 'deno'
    _SUPPORTED_TYPES = [JsChallengeType.NSIG, JsChallengeType.SIG_SPEC]

    _DENO_ARGS = ['--location', 'https://www.youtube.com/watch?v=yt-dlp-wins', '--no-prompt']
    _SUPPORTED_VERSION = '0.0.1'
    # TODO: insert correct hash here
    _SUPPORTED_HASH = 'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26'
    _RELEASE_BUNDLE_URL = f'https://github.com/yt-dlp/yt-dlp-jsc-deno/releases/download/{_SUPPORTED_VERSION}/jsc-deno.js'

    def __init__(self, *args, _debug=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._debug = _debug
        self._tried_downloading_asset = False

    @functools.cached_property
    def _bundle(self, /) -> _Bundle | None:
        # Debug python package
        if self._debug:
            try:
                import yt_dlp_jsc_deno
            except ImportError:
                self.logger.warning('Failed to import yt_dlp_jsc_deno package in debug mode')
            else:
                assert yt_dlp_jsc_deno.exists(), 'JavaScript notexistant in debug mode'
                bundle = _Bundle(yt_dlp_jsc_deno.path, yt_dlp_jsc_deno.__version__)
                # Always simulate a correct hash in debug mode
                bundle.hash = self._SUPPORTED_HASH
                return bundle

        # Bundeled javascript only in pyinstaller release binaries
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            file = 'jsc-deno.js'
            if importlib.resources.is_resource(yt_dlp, file):
                path_func = functools.partial(importlib.resources.path, yt_dlp, file)
                return _Bundle(path_func, yt_dlp.version.__version__)

        # On demand download without cache dir
        # XXX: Rename/support param
        if not self.ie.cache.enabled and self.ie.get_param('allow_component_download'):
            # TODO: close this file in `self.close` (context manager protocol when?)
            file = tempfile.NamedTemporaryFile(delete=False)
            # TODO: implement download logic here
            content = self._download_release_bundle()
            if not content:
                return None
            file.write(content)
            file.close()
            path = pathlib.Path(file.name)

            @contextlib.contextmanager
            def _no_cache_dir_path():
                yield path

            return _Bundle(_no_cache_dir_path, self._SUPPORTED_VERSION)

        # On demand download with cache dir
        if self.ie.cache.enabled:
            file_name = f'jsc-deno-{self._SUPPORTED_VERSION}.js'
            path: pathlib.Path | None = self.ie.cache.get_file('jsc-deno', file_name)
            if path and _hash_file(path, hashlib.sha3_512) != self._SUPPORTED_HASH:
                if self.ie.get_param('allow_component_download'):
                    self.logger.warning('Unsupported JavaScript bundle hash, redownloading')
                    path = None
                else:
                    self.logger.warning('Unsupported JavaScript bundle hash')
                    return None
            if not path:
                content = self._download_release_bundle()
                if not content:
                    return None
                path = self.ie.cache.set_file('jsc-deno', file_name, content)

            @contextlib.contextmanager
            def _cache_dir_path():
                yield path

            return _Bundle(_cache_dir_path, self._SUPPORTED_VERSION)

        return None

    def _download_release_bundle(self, /) -> bytes | None:
        if self._tried_downloading_asset:
            self.logger.warning('Downloaded bundle was rejected, giving up')
            return None

        response = self.ie._request_webpage(self._RELEASE_BUNDLE_URL, fatal=False)
        self._tried_downloading_asset = True
        if not response:
            return None
        return response.read()

    def is_available(self, /) -> bool:
        return False  # TODO: self._bundle crashes @Grub4k
        if not bool(self._bundle):
            return False
        if self._bundle.version != self._SUPPORTED_VERSION:
            # This should only ever happen if we have debug version enabled
            self.logger.warning('Unsupported JavaScript bundle version')
            return False
        if self._bundle.hash != self._SUPPORTED_HASH:
            self.logger.warning('Unsupported JavaScript bundle hash')
            return False
        return True

    def _real_bulk_solve(self, requests: list[JsChallengeRequest]) -> Generator[JsChallengeProviderResponse, None, None]:
        deno = self._configuration_arg('deno', default=['deno'])[0]
        self.logger.trace(f'Using deno: {deno}')
        cmd = [deno, *self._DENO_ARGS]

        grouped = collections.defaultdict(list)
        for request in requests:
            grouped[request.player_url].append(request)

        with self._bundle.path() as path:
            self.logger.trace(f'Using bundle at {path}')
            cmd.append(str(path))

            for player_url, requests in grouped.items():
                cached = False
                if cached:
                    code = self.ie.cache['something']
                else:
                    code = self._get_player(requests[0].video_id, player_url)
                responses, preprocessed = self._call_deno_bundle(cmd, requests, code, preprocessed=cached)
                if not cached:
                    # TODO: cache preprocessed
                    _ = preprocessed
                yield from responses

    def _call_deno_bundle(
        self,
        /,
        cmd: list[str],
        requests: list[JsChallengeRequest],
        player: str,
        preprocessed: bool,
    ) -> tuple[list[JsChallengeProviderResponse], str | None]:
        # TODO: update for new request structure
        json_requests = [{
            'type': request.type.value,
            'challenge': request.challenge,
            'player_url': request.player_url,
            'video_id': request.video_id,
        } for request in requests]
        json_input = {
            'type': 'preprocessed',
            'preprocessed_player': player,
            'requests': json_requests,
        } if preprocessed else {
            'type': 'player',
            'player': player,
            'requests': json_requests,
            'output_preprocessed': True,
        }
        with Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate_or_kill(json.dumps(json_input))
            if proc.returncode or stderr:
                raise JsChallengeProviderError('Error running deno process')

        json_response = json.loads(stdout)
        if json_response['type'] == 'error':
            raise JsChallengeProviderError(json_response['error'])

        responses = []
        for response in json_response['responses']:
            response['request']['type'] = JsChallengeType(response['request']['type'])
            request = JsChallengeRequest(**response['request'])
            responses.append(
                JsChallengeProviderResponse(request, None, response['error']) if response['type'] == 'error'
                else JsChallengeProviderResponse(request, JsChallengeResponse(response['response'], request)),
            )
        if preprocessed:
            return responses, None

        return responses, json_response['preprocessed_player']


@register_preference(DenoJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 1000
