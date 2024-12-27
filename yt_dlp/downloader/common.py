import contextlib
import errno
import functools
import os
import random
import re
import threading
import time

from ..minicurses import (
    BreaklineStatusPrinter,
    MultilineLogger,
    MultilinePrinter,
    QuietMultilinePrinter,
)
from ..utils import (
    IDENTITY,
    NO_DEFAULT,
    LockingUnsupportedError,
    Namespace,
    RetryManager,
    classproperty,
    deprecation_warning,
    format_bytes,
    join_nonempty,
    parse_bytes,
    remove_start,
    sanitize_open,
    shell_quote,
    timeconvert,
    timetuple_from_msec,
    try_call,
)
from ..utils._utils import _ProgressState


class FileDownloader:
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
    retries:            Number of times to retry for expected network errors.
                        Default is 0 for API, but 10 for CLI
    file_access_retries:   Number of times to retry on file access error (default: 3)
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
    progress_delta:     The minimum time between progress output, in seconds
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
    retry_sleep_functions: See YoutubeDL.py

    Subclasses of this one must re-define the real_download method.
    """

    _TEST_FILE_SIZE = 10241
    params = None

    def __init__(self, ydl, params):
        """Create a FileDownloader object with the given options."""
        self._set_ydl(ydl)
        self._progress_hooks = []
        self.params = params
        self._prepare_multiline_status()
        self.add_progress_hook(self.report_progress)
        if self.params.get('progress_delta'):
            self._progress_delta_lock = threading.Lock()
            self._progress_delta_time = time.monotonic()

    def _set_ydl(self, ydl):
        self.ydl = ydl

        for func in (
            'deprecation_warning',
            'deprecated_feature',
            'report_error',
            'report_file_already_downloaded',
            'report_warning',
            'to_console_title',
            'to_stderr',
            'trouble',
            'write_debug',
        ):
            if not hasattr(self, func):
                setattr(self, func, getattr(ydl, func))

    def to_screen(self, *args, **kargs):
        self.ydl.to_screen(*args, quiet=self.params.get('quiet'), **kargs)

    __to_screen = to_screen

    @classproperty
    def FD_NAME(cls):
        return re.sub(r'(?<=[a-z])(?=[A-Z])', '_', cls.__name__[:-2]).lower()

    @staticmethod
    def format_seconds(seconds):
        if seconds is None:
            return ' Unknown'
        time = timetuple_from_msec(seconds * 1000)
        if time.hours > 99:
            return '--:--:--'
        return '%02d:%02d:%02d' % time[:-1]

    @classmethod
    def format_eta(cls, seconds):
        return f'{remove_start(cls.format_seconds(seconds), "00:"):>8s}'

    @staticmethod
    def calc_percent(byte_counter, data_len):
        if data_len is None:
            return None
        return float(byte_counter) / float(data_len) * 100.0

    @staticmethod
    def format_percent(percent):
        return '  N/A%' if percent is None else f'{percent:>5.1f}%'

    @classmethod
    def calc_eta(cls, start_or_rate, now_or_remaining, total=NO_DEFAULT, current=NO_DEFAULT):
        if total is NO_DEFAULT:
            rate, remaining = start_or_rate, now_or_remaining
            if None in (rate, remaining):
                return None
            return int(float(remaining) / rate)

        start, now = start_or_rate, now_or_remaining
        if total is None:
            return None
        if now is None:
            now = time.time()
        rate = cls.calc_speed(start, now, current)
        return rate and int((float(total) - float(current)) / rate)

    @staticmethod
    def calc_speed(start, now, bytes):
        dif = now - start
        if bytes == 0 or dif < 0.001:  # One millisecond
            return None
        return float(bytes) / dif

    @staticmethod
    def format_speed(speed):
        return ' Unknown B/s' if speed is None else f'{format_bytes(speed):>10s}/s'

    @staticmethod
    def format_retries(retries):
        return 'inf' if retries == float('inf') else int(retries)

    @staticmethod
    def filesize_or_none(unencoded_filename):
        if os.path.isfile(unencoded_filename):
            return os.path.getsize(unencoded_filename)
        return 0

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
        deprecation_warning('yt_dlp.FileDownloader.parse_bytes is deprecated and '
                            'may be removed in the future. Use yt_dlp.utils.parse_bytes instead')
        return parse_bytes(bytestr)

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
                (os.path.exists(filename) and not os.path.isfile(filename)):
            return filename
        return filename + '.part'

    def undo_temp_name(self, filename):
        if filename.endswith('.part'):
            return filename[:-len('.part')]
        return filename

    def ytdl_filename(self, filename):
        return filename + '.ytdl'

    def wrap_file_access(action, *, fatal=False):
        def error_callback(err, count, retries, *, fd):
            return RetryManager.report_retry(
                err, count, retries, info=fd.__to_screen,
                warn=lambda e: (time.sleep(0.01), fd.to_screen(f'[download] Unable to {action} file: {e}')),
                error=None if fatal else lambda e: fd.report_error(f'Unable to {action} file: {e}'),
                sleep_func=fd.params.get('retry_sleep_functions', {}).get('file_access'))

        def wrapper(self, func, *args, **kwargs):
            for retry in RetryManager(self.params.get('file_access_retries', 3), error_callback, fd=self):
                try:
                    return func(self, *args, **kwargs)
                except OSError as err:
                    if err.errno in (errno.EACCES, errno.EINVAL):
                        retry.error = err
                        continue
                    retry.error_callback(err, 1, 0)

        return functools.partial(functools.partialmethod, wrapper)

    @wrap_file_access('open', fatal=True)
    def sanitize_open(self, filename, open_mode):
        f, filename = sanitize_open(filename, open_mode)
        if not getattr(f, 'locked', None):
            self.write_debug(f'{LockingUnsupportedError.msg}. Proceeding without locking', only_once=True)
        return f, filename

    @wrap_file_access('remove')
    def try_remove(self, filename):
        if os.path.isfile(filename):
            os.remove(filename)

    @wrap_file_access('rename')
    def try_rename(self, old_filename, new_filename):
        if old_filename == new_filename:
            return
        os.replace(old_filename, new_filename)

    def try_utime(self, filename, last_modified_hdr):
        """Try to set the last-modified time of the given file."""
        if last_modified_hdr is None:
            return
        if not os.path.isfile(filename):
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
        with contextlib.suppress(Exception):
            os.utime(filename, (time.time(), filetime))
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
            self._multiline = BreaklineStatusPrinter(self.ydl._out_files.out, lines)
        else:
            self._multiline = MultilinePrinter(self.ydl._out_files.out, lines, not self.params.get('quiet'))
        self._multiline.allow_colors = self.ydl._allow_colors.out and self.ydl._allow_colors.out != 'no_color'
        self._multiline._HAVE_FULLCAP = self.ydl._allow_colors.out

    def _finish_multiline_status(self):
        self._multiline.end()

    ProgressStyles = Namespace(
        downloaded_bytes='light blue',
        percent='light blue',
        eta='yellow',
        speed='green',
        elapsed='bold white',
        total_bytes='',
        total_bytes_estimate='',
    )

    def _report_progress_status(self, s, default_template):
        for name, style in self.ProgressStyles.items_:
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
            progress_dict), _ProgressState.from_dict(s), s.get('_percent'))

    def _format_progress(self, *args, **kwargs):
        return self.ydl._format_text(
            self._multiline.stream, self._multiline.allow_colors, *args, **kwargs)

    def report_progress(self, s):
        def with_fields(*tups, default=''):
            for *fields, tmpl in tups:
                if all(s.get(f) is not None for f in fields):
                    return tmpl
            return default

        _format_bytes = lambda k: f'{format_bytes(s.get(k)):>10s}'

        if s['status'] == 'finished':
            if self.params.get('noprogress'):
                self.to_screen('[download] Download completed')
            speed = try_call(lambda: s['total_bytes'] / s['elapsed'])
            s.update({
                'speed': speed,
                '_speed_str': self.format_speed(speed).strip(),
                '_total_bytes_str': _format_bytes('total_bytes'),
                '_elapsed_str': self.format_seconds(s.get('elapsed')),
                '_percent': 100.0,
                '_percent_str': self.format_percent(100),
            })
            self._report_progress_status(s, join_nonempty(
                '100%%',
                with_fields(('total_bytes', 'of %(_total_bytes_str)s')),
                with_fields(('elapsed', 'in %(_elapsed_str)s')),
                with_fields(('speed', 'at %(_speed_str)s')),
                delim=' '))

        if s['status'] != 'downloading':
            return

        if update_delta := self.params.get('progress_delta'):
            with self._progress_delta_lock:
                if time.monotonic() < self._progress_delta_time:
                    return
                self._progress_delta_time += update_delta

        progress = try_call(
            lambda: 100 * s['downloaded_bytes'] / s['total_bytes'],
            lambda: 100 * s['downloaded_bytes'] / s['total_bytes_estimate'],
            lambda: s['downloaded_bytes'] == 0 and 0)
        s.update({
            '_eta_str': self.format_eta(s.get('eta')).strip(),
            '_speed_str': self.format_speed(s.get('speed')),
            '_percent': progress,
            '_percent_str': self.format_percent(progress),
            '_total_bytes_str': _format_bytes('total_bytes'),
            '_total_bytes_estimate_str': _format_bytes('total_bytes_estimate'),
            '_downloaded_bytes_str': _format_bytes('downloaded_bytes'),
            '_elapsed_str': self.format_seconds(s.get('elapsed')),
        })

        msg_template = with_fields(
            ('total_bytes', '%(_percent_str)s of %(_total_bytes_str)s at %(_speed_str)s ETA %(_eta_str)s'),
            ('total_bytes_estimate', '%(_percent_str)s of ~%(_total_bytes_estimate_str)s at %(_speed_str)s ETA %(_eta_str)s'),
            ('downloaded_bytes', 'elapsed', '%(_downloaded_bytes_str)s at %(_speed_str)s (%(_elapsed_str)s)'),
            ('downloaded_bytes', '%(_downloaded_bytes_str)s at %(_speed_str)s'),
            default='%(_percent_str)s at %(_speed_str)s ETA %(_eta_str)s')

        msg_template += with_fields(
            ('fragment_index', 'fragment_count', ' (frag %(fragment_index)s/%(fragment_count)s)'),
            ('fragment_index', ' (frag %(fragment_index)s)'))
        self._report_progress_status(s, msg_template)

    def report_resuming_byte(self, resume_len):
        """Report attempt to resume at given byte."""
        self.to_screen(f'[download] Resuming download at byte {resume_len}')

    def report_retry(self, err, count, retries, frag_index=NO_DEFAULT, fatal=True):
        """Report retry"""
        is_frag = False if frag_index is NO_DEFAULT else 'fragment'
        RetryManager.report_retry(
            err, count, retries, info=self.__to_screen,
            warn=lambda msg: self.__to_screen(f'[download] Got error: {msg}'),
            error=IDENTITY if not fatal else lambda e: self.report_error(f'\r[download] Got error: {e}'),
            sleep_func=self.params.get('retry_sleep_functions', {}).get(is_frag or 'http'),
            suffix=f'fragment{"s" if frag_index is None else f" {frag_index}"}' if is_frag else None)

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
            and os.path.exists(filename)
        )

        if not hasattr(filename, 'write'):
            continuedl_and_exists = (
                self.params.get('continuedl', True)
                and os.path.isfile(filename)
                and not self.params.get('nopart', False)
            )

            # Check file already present
            if filename != '-' and (nooverwrites_and_exists or continuedl_and_exists):
                self.report_file_already_downloaded(filename)
                self._hook_progress({
                    'filename': filename,
                    'status': 'finished',
                    'total_bytes': os.path.getsize(filename),
                }, info_dict)
                self._finish_multiline_status()
                return True, False

        if subtitle:
            sleep_interval = self.params.get('sleep_interval_subtitles') or 0
        else:
            min_sleep_interval = self.params.get('sleep_interval') or 0
            sleep_interval = random.uniform(
                min_sleep_interval, self.params.get('max_sleep_interval') or min_sleep_interval)
        if sleep_interval > 0:
            self.to_screen(f'[download] Sleeping {sleep_interval:.2f} seconds ...')
            time.sleep(sleep_interval)

        ret = self.real_download(filename, info_dict)
        self._finish_multiline_status()
        return ret, True

    def real_download(self, filename, info_dict):
        """Real download process. Redefine in subclasses."""
        raise NotImplementedError('This method must be implemented by subclasses')

    def _hook_progress(self, status, info_dict):
        # Ideally we want to make a copy of the dict, but that is too slow
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

        if exe is None:
            exe = os.path.basename(args[0])

        self.write_debug(f'{exe} command line: {shell_quote(args)}')
