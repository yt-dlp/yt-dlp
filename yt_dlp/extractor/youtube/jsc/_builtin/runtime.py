from __future__ import annotations

import contextlib
import functools
import hashlib
import importlib.resources
import pathlib
import sys
import tempfile

import yt_dlp.version
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
)
from yt_dlp.utils._jsruntime import JsRuntimeInfo

TYPE_CHECKING = False
if TYPE_CHECKING:
    import typing
    from collections.abc import Callable


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


class JsRuntimeJCPBase(JsChallengeProvider):
    JS_RUNTIME_NAME: str
    _SUPPORTED_VERSION = '0.0.1'
    # TODO: insert correct hash here
    _SUPPORTED_HASH = 'a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a615b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26'
    _RELEASE_BUNDLE_URL = f'https://github.com/yt-dlp/yt-dlp-jsc-deno/releases/download/{_SUPPORTED_VERSION}/jsc-deno.js'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._debug = self.settings.get('debug', [None]) == 'true'
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

    @property
    def runtime_info(self) -> JsRuntimeInfo | bool:
        runtime = self.ie._downloader._js_runtimes.get(self.JS_RUNTIME_NAME)
        if not runtime or not runtime.info or not runtime.info.supported:
            return False
        return runtime.info

    def is_available(self, /) -> bool:
        if not self.runtime_info:
            return False
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
