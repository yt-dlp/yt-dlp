from __future__ import unicode_literals
import os
import subprocess

from .common import PostProcessor
from ..compat import compat_shlex_split
from ..utils import (
    check_executable,
    encodeArgument,
    shell_quote,
    PostProcessingError,
)


class SponSkrubPP(PostProcessor):
    _temp_ext = 'spons'
    _def_args = []
    _exe_name = 'sponskrub'

    def __init__(self, downloader, path='', args=None, ignoreerror=False, cut=False, force=False):
        PostProcessor.__init__(self, downloader)
        self.force = force
        self.cutout = cut
        self.args = ['-chapter'] if not cut else []
        self.args += self._configuration_args(self._def_args) if args is None else compat_shlex_split(args)
        self.path = self.get_exe(path)

        if not ignoreerror and self.path is None:
            if path:
                raise PostProcessingError('sponskrub not found in "%s"' % path)
            else:
                raise PostProcessingError('sponskrub not found. Please install or provide the path using --sponskrub-path.')

    def get_exe(self, path=''):
        if not path or not check_executable(path, ['-h']):
            path = os.path.join(path, self._exe_name)
            if not check_executable(path, ['-h']):
                return None
        return path

    def run(self, information):
        if self.path is None:
            return [], information

        if information['extractor_key'].lower() != 'youtube':
            self.to_screen('Skipping sponskrub since it is not a YouTube video')
            return [], information
        if self.cutout and not self.force and not information.get('__real_download', False):
            self.report_warning(
                'Skipping sponskrub since the video was already downloaded. '
                'Use --sponskrub-force to run sponskrub anyway')
            return [], information

        self.to_screen('Trying to %s sponsor sections' % ('remove' if self.cutout else 'mark'))
        if self.cutout:
            self.report_warning('Cutting out sponsor segments will cause the subtitles to go out of sync.')
            if not information.get('__real_download', False):
                self.report_warning('If sponskrub is run multiple times, unintended parts of the video could be cut out.')

        filename = information['filepath']
        temp_filename = filename + '.' + self._temp_ext + os.path.splitext(filename)[1]
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        cmd = [self.path]
        if self.args:
            cmd += self.args
        cmd += ['--', information['id'], filename, temp_filename]
        cmd = [encodeArgument(i) for i in cmd]

        self.write_debug('sponskrub command line: %s' % shell_quote(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout, stderr = p.communicate()

        if p.returncode == 0:
            os.remove(filename)
            os.rename(temp_filename, filename)
            self.to_screen('Sponsor sections have been %s' % ('removed' if self.cutout else 'marked'))
        elif p.returncode == 3:
            self.to_screen('No segments in the SponsorBlock database')
        else:
            stderr = stderr.decode('utf-8', 'replace')
            msg = stderr.strip()
            if not self.get_param('verbose', False):
                msg = msg.split('\n')[-1]
            raise PostProcessingError(msg if msg else 'sponskrub failed with error code %s!' % p.returncode)
        return [], information
