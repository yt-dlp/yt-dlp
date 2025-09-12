from __future__ import annotations
import abc
import dataclasses
import functools

from ._utils import _get_exe_version_output, detect_exe_version


@dataclasses.dataclass(frozen=True)
class JsRuntimeInfo:
    name: str
    path: str
    version: str
    supported: bool = True


class JsRuntime(abc.ABC):
    def __init__(self, path=None):
        self._path = path

    @functools.cached_property
    def info(self) -> JsRuntimeInfo | None:
        return self._info()

    @abc.abstractmethod
    def _info(self) -> JsRuntimeInfo | None:
        raise NotImplementedError


class DenoJsRuntime(JsRuntime):
    def _info(self):
        deno_path = self._path or 'deno'
        out = _get_exe_version_output(deno_path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^deno (\S+)')
        return JsRuntimeInfo(name='deno', path=deno_path, version=version)


class BunJsRuntime(JsRuntime):
    def _info(self):
        path = self._path or 'bun'
        out = _get_exe_version_output(path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^(\S+)')
        return JsRuntimeInfo(name='bun', path=path, version=version)


class NodeJsRuntime(JsRuntime):
    def _info(self):
        node_path = self._path or 'node'
        out = _get_exe_version_output(node_path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^v(\S+)')
        return JsRuntimeInfo(name='node', path=node_path, version=version)
