from __future__ import annotations
import dataclasses
import functools
from ._utils import _get_exe_version_output, detect_exe_version


@dataclasses.dataclass(frozen=True)
class RuntimeInfo:
    name: str
    path: str
    version: str
    supported: bool = True


class JsRuntime:
    def __init__(self, path=None):
        self._path = path

    @functools.cached_property
    def info(self) -> RuntimeInfo | None:
        return self._info()

    def _info(self) -> RuntimeInfo | None:
        raise NotImplementedError


class DenoJsRuntime(JsRuntime):
    def _info(self):
        deno_path = self._path or 'deno'
        out = _get_exe_version_output(deno_path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^deno (\S+)')
        return RuntimeInfo(name='deno', path=deno_path, version=version)


class NodeJsRuntime(JsRuntime):
    def _info(self):
        node_path = self._path or 'node'
        out = _get_exe_version_output(node_path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^v(\S+)')
        return RuntimeInfo(name='node', path=node_path, version=version)
