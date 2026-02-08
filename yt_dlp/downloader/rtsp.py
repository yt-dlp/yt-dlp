import os
import subprocess

from .common import FileDownloader
from ..utils import check_executable


class RtspFD(FileDownloader):
    def real_download(self, filename, info_dict):
        url = info_dict['url']
        self.report_destination(filename)
        tmpfilename = self.temp_name(filename)

        if check_executable('mplayer', ['-h']):
            args = [
                'mplayer', '-really-quiet', '-vo', 'null', '-vc', 'dummy',
                '-dumpstream', '-dumpfile', tmpfilename, url]
        elif check_executable('mpv', ['-h']):
            args = [
                'mpv', '-really-quiet', '--vo=null', '--stream-dump=' + tmpfilename, url]
        else:
            self.report_error('MMS or RTSP download detected but neither "mplayer" nor "mpv" could be run. Please install one')
            return False

        self._debug_cmd(args)

        retval = subprocess.call(args)
        if retval == 0:
            fsize = os.path.getsize(tmpfilename)
            self.to_screen(f'\r[{args[0]}] {fsize} bytes')
            self.try_rename(tmpfilename, filename)
            self._hook_progress({
                'downloaded_bytes': fsize,
                'total_bytes': fsize,
                'filename': filename,
                'status': 'finished',
            }, info_dict)
            return True
        else:
            self.to_stderr('\n')
            self.report_error('%s exited with code %d' % (args[0], retval))
            return False
