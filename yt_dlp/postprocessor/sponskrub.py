from __future__ import unicode_literals
import os
import subprocess

from .common import PostProcessor
from ..compat import compat_shlex_split
from ..utils import (
    check_executable,
    cli_option,
    encodeArgument,
    encodeFilename,
    shell_quote,
    str_or_none,
    Popen,
    PostProcessingError,
    prepend_extension,
)


# Deprecated in favor of the native implementation
class SponSkrubPP(PostProcessor):
    _temp_ext = 'spons'
    _exe_name = 'sponskrub'

    def __init__(self, downloader, path='', args=None, ignoreerror=False, cut=False, force=False, _from_cli=False):
        PostProcessor.__init__(self, downloader)
        self.force = force
        self.cutout = cut
        self.args = str_or_none(args) or ''  # For backward compatibility
        self.path = self.get_exe(path)

        if not _from_cli:
            self.deprecation_warning(
                'yt_dlp.postprocessor.SponSkrubPP support is deprecated and may be removed in a future version. '
                'Use yt_dlp.postprocessor.SponsorBlock and yt_dlp.postprocessor.ModifyChaptersPP instead')

        if not ignoreerror and self.path is None:
            if path:
                raise PostProcessingError('sponskrub not found in "%s"' % path)
            else:
                raise PostProcessingError('sponskrub not found. Please install or provide the path using --sponskrub-path')

    def get_exe(self, path=''):
        if not path or not check_executable(path, ['-h']):
            path = os.path.join(path, self._exe_name)
            if not check_executable(path, ['-h']):
                return None
        return path

    @PostProcessor._restrict_to(images=False)
    def run(self, information):
        if self.path is None:
            return [], information

        filename = information['filepath']
        if not os.path.exists(encodeFilename(filename)):  # no download
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

        temp_filename = prepend_extension(filename, self._temp_ext)
        if os.path.exists(encodeFilename(temp_filename)):
            os.remove(encodeFilename(temp_filename))

        cmd = [self.path]
        if not self.cutout:
            cmd += ['-chapter']
        cmd += cli_option(self._downloader.params, '-proxy', 'proxy')
        cmd += compat_shlex_split(self.args)  # For backward compatibility
        cmd += self._configuration_args(self._exe_name, use_compat=False)
        cmd += ['--', information['id'], filename, temp_filename]
        cmd = [encodeArgument(i) for i in cmd]

        self.write_debug('sponskrub command line: %s' % shell_quote(cmd))
        pipe = None if self.get_param('verbose') else subprocess.PIPE
        p = Popen(cmd, stdout=pipe)
        stdout = p.communicate_or_kill()[0]

        if p.returncode == 0:
            os.replace(temp_filename, filename)
            self.to_screen('Sponsor sections have been %s' % ('removed' if self.cutout else 'marked'))
        elif p.returncode == 3:
            self.to_screen('No segments in the SponsorBlock database')
        else:
            msg = stdout.decode('utf-8', 'replace').strip() if stdout else ''
            msg = msg.split('\n')[0 if msg.lower().startswith('unrecognised') else -1]
            raise PostProcessingError(msg if msg else 'sponskrub failed with error code %s' % p.returncode)
        return [], information
