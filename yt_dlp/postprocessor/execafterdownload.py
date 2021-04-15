from __future__ import unicode_literals

import re
import subprocess

from .common import PostProcessor
from ..compat import compat_shlex_quote
from ..utils import (
    encodeArgument,
    FORMAT_RE,
    PostProcessingError,
)


class ExecAfterDownloadPP(PostProcessor):

    def __init__(self, downloader, exec_cmd):
        super(ExecAfterDownloadPP, self).__init__(downloader)
        self.exec_cmd = exec_cmd

    @classmethod
    def pp_key(cls):
        return 'Exec'

    def parse_cmd(self, cmd, info):
        # If no %(key)s is found, replace {} for backard compatibility
        if not re.search(FORMAT_RE.format(r'[-\w>.+]+'), cmd):
            if '{}' not in cmd:
                cmd += ' {}'
            return cmd.replace('{}', compat_shlex_quote(info['filepath']))

        tmpl, info_copy = self._downloader.prepare_outtmpl(cmd, info)
        return tmpl % info_copy

    def run(self, info):
        cmd = self.parse_cmd(self.exec_cmd, info)
        self.to_screen('Executing command: %s' % cmd)
        retCode = subprocess.call(encodeArgument(cmd), shell=True)
        if retCode != 0:
            raise PostProcessingError('Command returned error code %d' % retCode)
        return [], info
