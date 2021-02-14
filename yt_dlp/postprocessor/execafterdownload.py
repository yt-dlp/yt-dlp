from __future__ import unicode_literals

import subprocess

from .common import PostProcessor
from ..compat import compat_shlex_quote
from ..utils import (
    encodeArgument,
    PostProcessingError,
)


class ExecAfterDownloadPP(PostProcessor):

    def __init__(self, downloader, exec_cmd):
        super(ExecAfterDownloadPP, self).__init__(downloader)
        self.exec_cmd = exec_cmd

    @classmethod
    def pp_key(cls):
        return 'Exec'

    def run(self, information):
        cmd = self.exec_cmd
        if '{}' not in cmd:
            cmd += ' {}'

        cmd = cmd.replace('{}', compat_shlex_quote(information['filepath']))

        self.to_screen('Executing command: %s' % cmd)
        retCode = subprocess.call(encodeArgument(cmd), shell=True)
        if retCode != 0:
            raise PostProcessingError(
                'Command returned error code %d' % retCode)

        return [], information
