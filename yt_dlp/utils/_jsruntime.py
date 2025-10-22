from __future__ import annotations
import abc
import dataclasses
import functools

from ._utils import _get_exe_version_output, detect_exe_version, int_or_none


def version_tuple(v):
    return tuple(int_or_none(x, default=0) for x in v.split('.'))


@dataclasses.dataclass(frozen=True)
class JsRuntimeInfo:
    name: str
    path: str
    version: str
    version_tuple: tuple[int, ...]
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
    MIN_SUPPORTED_VERSION = (2, 0, 0)

    def _info(self):
        path = self._path or 'deno'
        out = _get_exe_version_output(path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^deno (\S+)')
        vt = version_tuple(version)
        return JsRuntimeInfo(
            name='deno', path=path, version=version, version_tuple=vt,
            supported=vt >= self.MIN_SUPPORTED_VERSION)


class BunJsRuntime(JsRuntime):
    MIN_SUPPORTED_VERSION = (1, 0, 31)

    def _info(self):
        path = self._path or 'bun'
        out = _get_exe_version_output(path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^(\S+)')
        vt = version_tuple(version)
        return JsRuntimeInfo(
            name='bun', path=path, version=version, version_tuple=vt,
            supported=vt >= self.MIN_SUPPORTED_VERSION)


class NodeJsRuntime(JsRuntime):
    MIN_SUPPORTED_VERSION = (20, 0, 0)

    def _info(self):
        path = self._path or 'node'
        out = _get_exe_version_output(path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^v(\S+)')
        vt = version_tuple(version)
        return JsRuntimeInfo(
            name='node', path=path, version=version, version_tuple=vt,
            supported=vt >= self.MIN_SUPPORTED_VERSION)
