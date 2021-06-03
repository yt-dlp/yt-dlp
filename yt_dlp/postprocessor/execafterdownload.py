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

    def parse_cmd(self, cmd, info):
        tmpl, tmpl_dict = self._downloader.prepare_outtmpl(cmd, info)
        if tmpl_dict:  # if there are no replacements, tmpl_dict = {}
            return tmpl % tmpl_dict

        # If no replacements are found, replace {} for backard compatibility
        if '{}' not in cmd:
            cmd += ' {}'
        return cmd.replace('{}', compat_shlex_quote(info['filepath']))

    def run(self, info):
        cmd = self.parse_cmd(self.exec_cmd, info)
        self.to_screen('Executing command: %s' % cmd)
        retCode = subprocess.call(encodeArgument(cmd), shell=True)
        if retCode != 0:
            raise PostProcessingError('Command returned error code %d' % retCode)
        return [], info
