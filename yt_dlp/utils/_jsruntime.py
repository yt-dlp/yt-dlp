from __future__ import annotations
import abc
import dataclasses
import functools
import os.path

from ._utils import _get_exe_version_output, detect_exe_version, int_or_none


# NOT public API
def runtime_version_tuple(v):
    # NB: will return (0,) if `v` is an invalid version string
    return tuple(int_or_none(x, default=0) for x in v.split('.'))


def _determine_runtime_path(path, basename):
    if not path:
        return basename
    if os.path.isdir(path):
        return os.path.join(path, basename)
    return path


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
        path = _determine_runtime_path(self._path, 'deno')
        out = _get_exe_version_output(path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^deno (\S+)', 'unknown')
        vt = runtime_version_tuple(version)
        return JsRuntimeInfo(
            name='deno', path=path, version=version, version_tuple=vt,
            supported=vt >= self.MIN_SUPPORTED_VERSION)


class BunJsRuntime(JsRuntime):
    MIN_SUPPORTED_VERSION = (1, 0, 31)

    def _info(self):
        path = _determine_runtime_path(self._path, 'bun')
        out = _get_exe_version_output(path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^(\S+)', 'unknown')
        vt = runtime_version_tuple(version)
        return JsRuntimeInfo(
            name='bun', path=path, version=version, version_tuple=vt,
            supported=vt >= self.MIN_SUPPORTED_VERSION)


class NodeJsRuntime(JsRuntime):
    MIN_SUPPORTED_VERSION = (20, 0, 0)

    def _info(self):
        path = _determine_runtime_path(self._path, 'node')
        out = _get_exe_version_output(path, ['--version'])
        if not out:
            return None
        version = detect_exe_version(out, r'^v(\S+)', 'unknown')
        vt = runtime_version_tuple(version)
        return JsRuntimeInfo(
            name='node', path=path, version=version, version_tuple=vt,
            supported=vt >= self.MIN_SUPPORTED_VERSION)


class QuickJsRuntime(JsRuntime):
    MIN_SUPPORTED_VERSION = (2023, 12, 9)

    def _info(self):
        path = _determine_runtime_path(self._path, 'qjs')
        # quickjs does not have --version and --help returns a status code of 1
        out = _get_exe_version_output(path, ['--help'], ignore_return_code=True)
        if not out:
            return None
        is_ng = 'QuickJS-ng' in out

        version = detect_exe_version(out, r'^QuickJS(?:-ng)?\s+version\s+(\S+)', 'unknown')
        vt = runtime_version_tuple(version.replace('-', '.'))
        if is_ng:
            return JsRuntimeInfo(
                name='quickjs-ng', path=path, version=version, version_tuple=vt,
                supported=vt > (0,))
        return JsRuntimeInfo(
            name='quickjs', path=path, version=version, version_tuple=vt,
            supported=vt >= self.MIN_SUPPORTED_VERSION)
