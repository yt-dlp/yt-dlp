from __future__ import annotations

import pathlib
import shlex
import subprocess
import tempfile

from yt_dlp.extractor.youtube.jsc._builtin.ejs import EJSBaseJCP
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeRequest,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.utils import Popen


@register_provider
class QuickJSJCP(EJSBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'quickjs'
    JS_RUNTIME_NAME = 'quickjs'
    _QJS_MIN_RECOMMENDED = {
        'quickjs': (2025, 4, 26),
        'quickjs-ng': (0, 12, 0),
    }
    _QJS_WARNING_TMPL = (
        '{name} versions older than {version} are missing important optimizations '
        'and will solve the JS challenges very slowly. Consider upgrading.')

    def _run_js_runtime(self, stdin: str, /) -> str:
        min_recommended_version = self._QJS_MIN_RECOMMENDED[self.runtime_info.name]
        if self.runtime_info.version_tuple < min_recommended_version:
            self.logger.warning(self._QJS_WARNING_TMPL.format(
                name=self.runtime_info.name,
                version='.'.join(map(str, min_recommended_version))))

        # QuickJS does not support reading from stdin, so we have to use a temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8')
        try:
            temp_file.write(stdin)
            temp_file.close()
            cmd = [self.runtime_info.path, '--script', temp_file.name]
            self.logger.debug(f'Running QuickJS: {shlex.join(cmd)}')
            with Popen(
                cmd,
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as proc:
                stdout, stderr = proc.communicate_or_kill()
                if proc.returncode or stderr:
                    msg = f'Error running QuickJS process (returncode: {proc.returncode})'
                    if stderr:
                        msg = f'{msg}: {stderr.strip()}'
                    raise JsChallengeProviderError(msg)
        finally:
            pathlib.Path(temp_file.name).unlink(missing_ok=True)

        return stdout


@register_preference(QuickJSJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 850
