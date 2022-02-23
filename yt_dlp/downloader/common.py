from __future__ import division, unicode_literals

import os
import re
import time
import random
import errno

from ..utils import (
    decodeArgument,
    encodeFilename,
    error_to_compat_str,
    format_bytes,
    sanitize_open,
    shell_quote,
    timeconvert,
    timetuple_from_msec,
)
from ..minicurses import (
    MultilineLogger,
    MultilinePrinter,
    QuietMultilinePrinter,
    BreaklineStatusPrinter
)


class FileDownloader(object):
    """File Downloader class.

    File downloader objects are the ones responsible of downloading the
    actual video file and writing it to disk.

    File downloaders accept a lot of parameters. In order not to saturate
    the object constructor with arguments, it receives a dictionary of
    options instead.

    Available options:

    verbose:            Print additional info to stdout.
    quiet:              Do not print messages to stdout.
    ratelimit:          Download speed limit, in bytes/sec.
    throttledratelimit: Assume the download is being throttled below this speed (bytes/sec)
    retries:            Number of times to retry for HTTP error 5xx
    file_access_retries:   Number of times to retry on file access error
    buffersize:         Size of download buffer in bytes.
    noresizebuffer:     Do not automatically resize the download buffer.
    continuedl:         Try to continue downloads if possible.
    noprogress:         Do not print the progress bar.
    nopart:             Do not use temporary .part files.
    updatetime:         Use the Last-modified header to set output file timestamps.
    test:               Download only first bytes to test the downloader.
    min_filesize:       Skip files smaller than this size
    max_filesize:       Skip files larger than this size
    xattr_set_filesize: Set ytdl.filesize user xattribute with expected size.
    external_downloader_args:  A dictionary of downloader keys (in lower case)
                        and a list of additional command-line arguments for the
                        executable. Use 'default' as the name for arguments to be
                        passed to all downloaders. For compatibility with youtube-dl,
                        a single list of args can also be used
    hls_use_mpegts:     Use the mpegts container for HLS videos.
    http_chunk_size:    Size of a chunk for chunk-based HTTP downloading. May be
                        useful for bypassing bandwidth throttling imposed by
                        a webserver (experimental)
    progress_template:  See YoutubeDL.py

    Subclasses of this one must re-define the real_download method.
    """

    _TEST_FILE_SIZE = 10241
    params = None

    def __init__(self, ydl, params):
        """Create a FileDownloader object with the given options."""
        self.ydl = ydl
        self._progress_hooks = []
        self.params = params
        self._prepare_multiline_status()
        self.add_progress_hook(self.report_progress)

    @staticmethod
    def format_seconds(seconds):
        time = timetuple_from_msec(seconds * 1000)
        if time.hours > 99:
            return '--:--:--'
        if not time.hours:
            return '%02d:%02d' % time[1:-1]
        return '%02d:%02d:%02d' % time[:-1]

    @staticmethod
    def calc_percent(byte_counter, data_len):
        if data_len is None:
            return None
        return float(byte_counter) / float(data_len) * 100.0

    @staticmethod
    def format_percent(percent):
        if percent is None:
            return '---.-%'
        elif percent == 100:
            return '100%'
        return '%6s' % ('%3.1f%%' % percent)

    @staticmethod
    def calc_eta(start, now, total, current):
        if total is None:
            return None
        if now is None:
            now = time.time()
        dif = now - start
        if current == 0 or dif < 0.001:  # One millisecond
            return None
        rate = float(current) / dif
        return int((float(total) - float(current)) / rate)

    @staticmethod
    def format_eta(eta):
        if eta is None:
            return '--:--'
        return FileDownloader.format_seconds(eta)

    @staticmethod
    def calc_speed(start, now, bytes):
        dif = now - start
        if bytes == 0 or dif < 0.001:  # One millisecond
            return None
        return float(bytes) / dif

    @staticmethod
    def format_speed(speed):
        if speed is None:
            return '%10s' % '---b/s'
        return '%10s' % ('%s/s' % format_bytes(speed))

    @staticmethod
    def format_retries(retries):
        return 'inf' if retries == float('inf') else '%.0f' % retries

    @staticmethod
    def best_block_size(elapsed_time, bytes):
        new_min = max(bytes / 2.0, 1.0)
        new_max = min(max(bytes * 2.0, 1.0), 4194304)  # Do not surpass 4 MB
        if elapsed_time < 0.001:
            return int(new_max)
        rate = bytes / elapsed_time
        if rate > new_max:
            return int(new_max)
        if rate < new_min:
            return int(new_min)
        return int(rate)

    @staticmethod
    def parse_bytes(bytestr):
        """Parse a string indicating a byte quantity into an integer."""
        matchobj = re.match(r'(?i)^(\d+(?:\.\d+)?)([kMGTPEZY]?)$', bytestr)
        if matchobj is None:
            return None
        number = float(matchobj.group(1))
        multiplier = 1024.0 ** 'bkmgtpezy'.index(matchobj.group(2).lower())
        return int(round(number * multiplier))

    def to_screen(self, *args, **kargs):
        self.ydl.to_stdout(*args, quiet=self.params.get('quiet'), **kargs)

    def to_stderr(self, message):
        self.ydl.to_stderr(message)

    def to_console_title(self, message):
        self.ydl.to_console_title(message)

    def trouble(self, *args, **kargs):
        self.ydl.trouble(*args, **kargs)

    def report_warning(self, *args, **kargs):
        self.ydl.report_warning(*args, **kargs)

    def report_error(self, *args, **kargs):
        self.ydl.report_error(*args, **kargs)

    def write_debug(self, *args, **kargs):
        self.ydl.write_debug(*args, **kargs)

    def slow_down(self, start_time, now, byte_counter):
        """Sleep if the download speed is over the rate limit."""
        rate_limit = self.params.get('ratelimit')
        if rate_limit is None or byte_counter == 0:
            return
        if now is None:
            now = time.time()
        elapsed = now - start_time
        if elapsed <= 0.0:
            return
        speed = float(byte_counter) / elapsed
        if speed > rate_limit:
            sleep_time = float(byte_counter) / rate_limit - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def temp_name(self, filename):
        """Returns a temporary filename for the given filename."""
        if self.params.get('nopart', False) or filename == '-' or \
                (os.path.exists(encodeFilename(filename)) and not os.path.isfile(encodeFilename(filename))):
            return filename
        return filename + '.part'

    def undo_temp_name(self, filename):
        if filename.endswith('.part'):
            return filename[:-len('.part')]
        return filename

    def ytdl_filename(self, filename):
        return filename + '.ytdl'

    def sanitize_open(self, filename, open_mode):
        file_access_retries = self.params.get('file_access_retries', 10)
        retry = 0
        while True:
            try:
                return sanitize_open(filename, open_mode)
            except (IOError, OSError) as err:
                retry = retry + 1
                if retry > file_access_retries or err.errno not in (errno.EACCES,):
                    raise
                self.to_screen(
                    '[download] Got file access error. Retrying (attempt %d of %s) ...'
                    % (retry, self.format_retries(file_access_retries)))
                time.sleep(0.01)

    def try_rename(self, old_filename, new_filename):
        if old_filename == new_filename:
            return
        try:
            os.replace(old_filename, new_filename)
        except (IOError, OSError) as err:
            self.report_error(f'unable to rename file: {err}')

    def try_utime(self, filename, last_modified_hdr):
        """Try to set the last-modified time of the given file."""
        if last_modified_hdr is None:
            return
        if not os.path.isfile(encodeFilename(filename)):
            return
        timestr = last_modified_hdr
        if timestr is None:
            return
        filetime = timeconvert(timestr)
        if filetime is None:
            return filetime
        # Ignore obviously invalid dates
        if filetime == 0:
            return
        try:
            os.utime(filename, (time.time(), filetime))
        except Exception:
            pass
        return filetime

    def report_destination(self, filename):
        """Report destination filename."""
        self.to_screen('[download] Destination: ' + filename)

    def _prepare_multiline_status(self, lines=1):
        if self.params.get('noprogress'):
            self._multiline = QuietMultilinePrinter()
        elif self.ydl.params.get('logger'):
            self._multiline = MultilineLogger(self.ydl.params['logger'], lines)
        elif self.params.get('progress_with_newline'):
            self._multiline = BreaklineStatusPrinter(self.ydl._screen_file, lines)
        else:
            self._multiline = MultilinePrinter(self.ydl._screen_file, lines, not self.params.get('quiet'))
        self._multiline.allow_colors = self._multiline._HAVE_FULLCAP and not self.params.get('no_color')

    def _finish_multiline_status(self):
        self._multiline.end()

    _progress_styles = {
        'downloaded_bytes': 'light blue',
        'percent': 'light blue',
        'eta': 'yellow',
        'speed': 'green',
        'elapsed': 'bold white',
        'total_bytes': '',
        'total_bytes_estimate': '',
    }

    def _report_progress_status(self, s, default_template):
        for name, style in self._progress_styles.items():
            name = f'_{name}_str'
            if name not in s:
                continue
            s[name] = self._format_progress(s[name], style)
        s['_default_template'] = default_template % s

        progress_dict = s.copy()
        progress_dict.pop('info_dict')
        progress_dict = {'info': s['info_dict'], 'progress': progress_dict}

        progress_template = self.params.get('progress_template', {})
        self._multiline.print_at_line(self.ydl.evaluate_outtmpl(
            progress_template.get('download') or '[download] %(progress._default_template)s',
            progress_dict), s.get('progress_idx') or 0)
        self.to_console_title(self.ydl.evaluate_outtmpl(
            progress_template.get('download-title') or 'yt-dlp %(progress._default_template)s',
            progress_dict))

    def _format_progress(self, *args, **kwargs):
        return self.ydl._format_text(
            self._multiline.stream, self._multiline.allow_colors, *args, **kwargs)

    def report_progress(self, s):
        if s['status'] == 'finished':
            if self.params.get('noprogress'):
                self.to_screen('[download] Download completed')
            msg_template = '100%%'
            if s.get('total_bytes') is not None:
                s['_total_bytes_str'] = format_bytes(s['total_bytes'])
                msg_template += ' of %(_total_bytes_str)s'
            if s.get('elapsed') is not None:
                s['_elapsed_str'] = self.format_seconds(s['elapsed'])
                msg_template += ' in %(_elapsed_str)s'
            s['_percent_str'] = self.format_percent(100)
            self._report_progress_status(s, msg_template)
            return

        if s['status'] != 'downloading':
            return

        if s.get('eta') is not None:
            s['_eta_str'] = self.format_eta(s['eta'])
        else:
            s['_eta_str'] = 'Unknown'

        if s.get('total_bytes') and s.get('downloaded_bytes') is not None:
            s['_percent_str'] = self.format_percent(100 * s['downloaded_bytes'] / s['total_bytes'])
        elif s.get('total_bytes_estimate') and s.get('downloaded_bytes') is not None:
            s['_percent_str'] = self.format_percent(100 * s['downloaded_bytes'] / s['total_bytes_estimate'])
        else:
            if s.get('downloaded_bytes') == 0:
                s['_percent_str'] = self.format_percent(0)
            else:
                s['_percent_str'] = 'Unknown %'

        if s.get('speed') is not None:
            s['_speed_str'] = self.format_speed(s['speed'])
        else:
            s['_speed_str'] = 'Unknown speed'

        if s.get('total_bytes') is not None:
            s['_total_bytes_str'] = format_bytes(s['total_bytes'])
            msg_template = '%(_percent_str)s of %(_total_bytes_str)s at %(_speed_str)s ETA %(_eta_str)s'
        elif s.get('total_bytes_estimate') is not None:
            s['_total_bytes_estimate_str'] = format_bytes(s['total_bytes_estimate'])
            msg_template = '%(_percent_str)s of ~%(_total_bytes_estimate_str)s at %(_speed_str)s ETA %(_eta_str)s'
        else:
            if s.get('downloaded_bytes') is not None:
                s['_downloaded_bytes_str'] = format_bytes(s['downloaded_bytes'])
                if s.get('elapsed'):
                    s['_elapsed_str'] = self.format_seconds(s['elapsed'])
                    msg_template = '%(_downloaded_bytes_str)s at %(_speed_str)s (%(_elapsed_str)s)'
                else:
                    msg_template = '%(_downloaded_bytes_str)s at %(_speed_str)s'
            else:
                msg_template = '%(_percent_str)s at %(_speed_str)s ETA %(_eta_str)s'
        if s.get('fragment_index') and s.get('fragment_count'):
            msg_template += ' (frag %(fragment_index)s/%(fragment_count)s)'
        elif s.get('fragment_index'):
            msg_template += ' (frag %(fragment_index)s)'
        self._report_progress_status(s, msg_template)

    def report_resuming_byte(self, resume_len):
        """Report attempt to resume at given byte."""
        self.to_screen('[download] Resuming download at byte %s' % resume_len)

    def report_retry(self, err, count, retries):
        """Report retry in case of HTTP error 5xx"""
        self.to_screen(
            '[download] Got server HTTP error: %s. Retrying (attempt %d of %s) ...'
            % (error_to_compat_str(err), count, self.format_retries(retries)))

    def report_file_already_downloaded(self, *args, **kwargs):
        """Report file has already been fully downloaded."""
        return self.ydl.report_file_already_downloaded(*args, **kwargs)

    def report_unable_to_resume(self):
        """Report it was impossible to resume download."""
        self.to_screen('[download] Unable to resume')

    @staticmethod
    def supports_manifest(manifest):
        """ Whether the downloader can download the fragments from the manifest.
        Redefine in subclasses if needed. """
        pass

    def download(self, filename, info_dict, subtitle=False):
        """Download to a filename using the info from info_dict
        Return True on success and False otherwise
        """

        nooverwrites_and_exists = (
            not self.params.get('overwrites', True)
            and os.path.exists(encodeFilename(filename))
        )

        if not hasattr(filename, 'write'):
            continuedl_and_exists = (
                self.params.get('continuedl', True)
                and os.path.isfile(encodeFilename(filename))
                and not self.params.get('nopart', False)
            )

            # Check file already present
            if filename != '-' and (nooverwrites_and_exists or continuedl_and_exists):
                self.report_file_already_downloaded(filename)
                self._hook_progress({
                    'filename': filename,
                    'status': 'finished',
                    'total_bytes': os.path.getsize(encodeFilename(filename)),
                }, info_dict)
                self._finish_multiline_status()
                return True, False

        if subtitle is False:
            min_sleep_interval = self.params.get('sleep_interval')
            if min_sleep_interval:
                max_sleep_interval = self.params.get('max_sleep_interval', min_sleep_interval)
                sleep_interval = random.uniform(min_sleep_interval, max_sleep_interval)
                self.to_screen(
                    '[download] Sleeping %s seconds ...' % (
                        int(sleep_interval) if sleep_interval.is_integer()
                        else '%.2f' % sleep_interval))
                time.sleep(sleep_interval)
        else:
            sleep_interval_sub = 0
            if type(self.params.get('sleep_interval_subtitles')) is int:
                sleep_interval_sub = self.params.get('sleep_interval_subtitles')
            if sleep_interval_sub > 0:
                self.to_screen(
                    '[download] Sleeping %s seconds ...' % (
                        sleep_interval_sub))
                time.sleep(sleep_interval_sub)
        ret = self.real_download(filename, info_dict)
        self._finish_multiline_status()
        return ret, True

    def real_download(self, filename, info_dict):
        """Real download process. Redefine in subclasses."""
        raise NotImplementedError('This method must be implemented by subclasses')

    def _hook_progress(self, status, info_dict):
        if not self._progress_hooks:
            return
        status['info_dict'] = info_dict
        # youtube-dl passes the same status object to all the hooks.
        # Some third party scripts seems to be relying on this.
        # So keep this behavior if possible
        for ph in self._progress_hooks:
            ph(status)

    def add_progress_hook(self, ph):
        # See YoutubeDl.py (search for progress_hooks) for a description of
        # this interface
        self._progress_hooks.append(ph)

    def _debug_cmd(self, args, exe=None):
        if not self.params.get('verbose', False):
            return

        str_args = [decodeArgument(a) for a in args]

        if exe is None:
            exe = os.path.basename(str_args[0])

        self.write_debug('%s command line: %s' % (exe, shell_quote(str_args)))
