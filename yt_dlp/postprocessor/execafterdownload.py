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

    def run(self, info):
        tmpl, info_copy = self._downloader.prepare_outtmpl(self.exec_cmd, info)
        cmd = tmpl % info_copy
        if cmd == self.exec_cmd:  # No replacements were made
            if '{}' not in self.exec_cmd:
                self.exec_cmd += ' {}'
            cmd = self.exec_cmd.replace('{}', compat_shlex_quote(info['filepath']))

        self.to_screen('Executing command: %s' % cmd)
        retCode = subprocess.call(encodeArgument(cmd), shell=True)
        if retCode != 0:
            raise PostProcessingError(
                'Command returned error code %d' % retCode)

        return [], info
