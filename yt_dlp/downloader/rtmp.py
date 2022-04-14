import os
import re
import subprocess
import time

from .common import FileDownloader
from ..compat import compat_str
from ..utils import (
    Popen,
    check_executable,
    encodeArgument,
    encodeFilename,
    get_exe_version,
)


def rtmpdump_version():
    return get_exe_version(
        'rtmpdump', ['--help'], r'(?i)RTMPDump\s*v?([0-9a-zA-Z._-]+)')


class RtmpFD(FileDownloader):
    def real_download(self, filename, info_dict):
        def run_rtmpdump(args):
            start = time.time()
            resume_percent = None
            resume_downloaded_data_len = None
            proc = Popen(args, stderr=subprocess.PIPE)
            cursor_in_new_line = True
            proc_stderr_closed = False
            try:
                while not proc_stderr_closed:
                    # read line from stderr
                    line = ''
                    while True:
                        char = proc.stderr.read(1)
                        if not char:
                            proc_stderr_closed = True
                            break
                        if char in [b'\r', b'\n']:
                            break
                        line += char.decode('ascii', 'replace')
                    if not line:
                        # proc_stderr_closed is True
                        continue
                    mobj = re.search(r'([0-9]+\.[0-9]{3}) kB / [0-9]+\.[0-9]{2} sec \(([0-9]{1,2}\.[0-9])%\)', line)
                    if mobj:
                        downloaded_data_len = int(float(mobj.group(1)) * 1024)
                        percent = float(mobj.group(2))
                        if not resume_percent:
                            resume_percent = percent
                            resume_downloaded_data_len = downloaded_data_len
                        time_now = time.time()
                        eta = self.calc_eta(start, time_now, 100 - resume_percent, percent - resume_percent)
                        speed = self.calc_speed(start, time_now, downloaded_data_len - resume_downloaded_data_len)
                        data_len = None
                        if percent > 0:
                            data_len = int(downloaded_data_len * 100 / percent)
                        self._hook_progress({
                            'status': 'downloading',
                            'downloaded_bytes': downloaded_data_len,
                            'total_bytes_estimate': data_len,
                            'tmpfilename': tmpfilename,
                            'filename': filename,
                            'eta': eta,
                            'elapsed': time_now - start,
                            'speed': speed,
                        }, info_dict)
                        cursor_in_new_line = False
                    else:
                        # no percent for live streams
                        mobj = re.search(r'([0-9]+\.[0-9]{3}) kB / [0-9]+\.[0-9]{2} sec', line)
                        if mobj:
                            downloaded_data_len = int(float(mobj.group(1)) * 1024)
                            time_now = time.time()
                            speed = self.calc_speed(start, time_now, downloaded_data_len)
                            self._hook_progress({
                                'downloaded_bytes': downloaded_data_len,
                                'tmpfilename': tmpfilename,
                                'filename': filename,
                                'status': 'downloading',
                                'elapsed': time_now - start,
                                'speed': speed,
                            }, info_dict)
                            cursor_in_new_line = False
                        elif self.params.get('verbose', False):
                            if not cursor_in_new_line:
                                self.to_screen('')
                            cursor_in_new_line = True
                            self.to_screen('[rtmpdump] ' + line)
                if not cursor_in_new_line:
                    self.to_screen('')
                return proc.wait()
            except BaseException:  # Including KeyboardInterrupt
                proc.kill()
                proc.wait()
                raise

        url = info_dict['url']
        player_url = info_dict.get('player_url')
        page_url = info_dict.get('page_url')
        app = info_dict.get('app')
        play_path = info_dict.get('play_path')
        tc_url = info_dict.get('tc_url')
        flash_version = info_dict.get('flash_version')
        live = info_dict.get('rtmp_live', False)
        conn = info_dict.get('rtmp_conn')
        protocol = info_dict.get('rtmp_protocol')
        real_time = info_dict.get('rtmp_real_time', False)
        no_resume = info_dict.get('no_resume', False)
        continue_dl = self.params.get('continuedl', True)

        self.report_destination(filename)
        tmpfilename = self.temp_name(filename)
        test = self.params.get('test', False)

        # Check for rtmpdump first
        if not check_executable('rtmpdump', ['-h']):
            self.report_error('RTMP download detected but "rtmpdump" could not be run. Please install')
            return False

        # Download using rtmpdump. rtmpdump returns exit code 2 when
        # the connection was interrupted and resuming appears to be
        # possible. This is part of rtmpdump's normal usage, AFAIK.
        basic_args = [
            'rtmpdump', '--verbose', '-r', url,
            '-o', tmpfilename]
        if player_url is not None:
            basic_args += ['--swfVfy', player_url]
        if page_url is not None:
            basic_args += ['--pageUrl', page_url]
        if app is not None:
            basic_args += ['--app', app]
        if play_path is not None:
            basic_args += ['--playpath', play_path]
        if tc_url is not None:
            basic_args += ['--tcUrl', tc_url]
        if test:
            basic_args += ['--stop', '1']
        if flash_version is not None:
            basic_args += ['--flashVer', flash_version]
        if live:
            basic_args += ['--live']
        if isinstance(conn, list):
            for entry in conn:
                basic_args += ['--conn', entry]
        elif isinstance(conn, compat_str):
            basic_args += ['--conn', conn]
        if protocol is not None:
            basic_args += ['--protocol', protocol]
        if real_time:
            basic_args += ['--realtime']

        args = basic_args
        if not no_resume and continue_dl and not live:
            args += ['--resume']
        if not live and continue_dl:
            args += ['--skip', '1']

        args = [encodeArgument(a) for a in args]

        self._debug_cmd(args, exe='rtmpdump')

        RD_SUCCESS = 0
        RD_FAILED = 1
        RD_INCOMPLETE = 2
        RD_NO_CONNECT = 3

        started = time.time()

        try:
            retval = run_rtmpdump(args)
        except KeyboardInterrupt:
            if not info_dict.get('is_live'):
                raise
            retval = RD_SUCCESS
            self.to_screen('\n[rtmpdump] Interrupted by user')

        if retval == RD_NO_CONNECT:
            self.report_error('[rtmpdump] Could not connect to RTMP server.')
            return False

        while retval in (RD_INCOMPLETE, RD_FAILED) and not test and not live:
            prevsize = os.path.getsize(encodeFilename(tmpfilename))
            self.to_screen('[rtmpdump] Downloaded %s bytes' % prevsize)
            time.sleep(5.0)  # This seems to be needed
            args = basic_args + ['--resume']
            if retval == RD_FAILED:
                args += ['--skip', '1']
            args = [encodeArgument(a) for a in args]
            retval = run_rtmpdump(args)
            cursize = os.path.getsize(encodeFilename(tmpfilename))
            if prevsize == cursize and retval == RD_FAILED:
                break
            # Some rtmp streams seem abort after ~ 99.8%. Don't complain for those
            if prevsize == cursize and retval == RD_INCOMPLETE and cursize > 1024:
                self.to_screen('[rtmpdump] Could not download the whole video. This can happen for some advertisements.')
                retval = RD_SUCCESS
                break
        if retval == RD_SUCCESS or (test and retval == RD_INCOMPLETE):
            fsize = os.path.getsize(encodeFilename(tmpfilename))
            self.to_screen('[rtmpdump] Downloaded %s bytes' % fsize)
            self.try_rename(tmpfilename, filename)
            self._hook_progress({
                'downloaded_bytes': fsize,
                'total_bytes': fsize,
                'filename': filename,
                'status': 'finished',
                'elapsed': time.time() - started,
            }, info_dict)
            return True
        else:
            self.to_stderr('\n')
            self.report_error('rtmpdump exited with code %d' % retval)
            return False
