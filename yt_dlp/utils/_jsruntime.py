from __future__ import annotations
import dataclasses
import functools
from ._utils import Popen
import subprocess


@dataclasses.dataclass(frozen=True)
class RuntimeInfo:
    name: str
    path: str
    version: str


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
        with Popen(
            [deno_path, '--version'],
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                return None

            return RuntimeInfo(
                name='deno',
                path=deno_path,
                version=stdout.splitlines()[0].split()[1],
            )
