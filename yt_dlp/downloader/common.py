import contextlib
import errno
import functools
import os
import random
import re
import time

from ..output.progress import ProgressReporter
from ..utils import (
    IDENTITY,
    NO_DEFAULT,
    LockingUnsupportedError,
    RetryManager,
    classproperty,
    decodeArgument,
    encodeFilename,
    format_bytes,
    remove_start,
    sanitize_open,
    shell_quote,
    timeconvert,
    timetuple_from_msec,
)


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
    continuedl:         Attempt to continue downloads if possible
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

    def _set_ydl(self, ydl):
        self.ydl = ydl
        self.logger = ydl.logger
        self.console = ydl.console

    def deprecation_warning(self, message, *, stacklevel=0):
        self.logger.deprecation_warning(message, stacklevel=stacklevel + 1)

    def deprecated_feature(self, message):
        self.logger.deprecated_feature(message)

    def report_error(self, message, tb=None, is_error=True):
        self.logger.handle_error(message, trace=tb, is_error=is_error)

    def report_file_already_downloaded(self, file_name):
        self.ydl.report_file_already_downloaded(file_name)

    def report_warning(self, message, only_once=False):
        self.logger.warning(message, once=only_once)

    def to_console_title(self, message):
        self.console.change_title(message)

    def to_screen(self, message, skip_eol=False, only_once=False):
        self.logger.info(message, newline=not skip_eol, quiet=self.params.get('quiet'), once=only_once)

    def to_stderr(self, message, only_once=False):
        self.logger.error(message, once=only_once)

    def trouble(self, message=None, tb=None, is_error=True):
        self.logger.handle_error(message, trace=tb, is_error=is_error, prefix=False)

    def write_debug(self, message, only_once=False):
        self.logger.debug(message, once=only_once)

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

    def wrap_file_access(action, *, fatal=False):
        def error_callback(err, count, retries, *, fd):
            return RetryManager.report_retry(
                err, count, retries, info=fd.to_screen,
                warn=lambda e: (time.sleep(0.01), fd.to_screen(f'[download] Unable to {action} file: {e}')),
                error=None if fatal else lambda e: fd.report_error(f'Unable to {action} file: {e}'),
                sleep_func=fd.params.get('retry_sleep_functions', {}).get('file_access'))

        def wrapper(self, func, *args, **kwargs):
            for retry in RetryManager(self.params.get('file_access_retries'), error_callback, fd=self):
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
        with contextlib.suppress(Exception):
            os.utime(filename, (time.time(), filetime))
        return filetime

    def report_destination(self, filename):
        """Report destination filename."""
        self.to_screen('[download] Destination: ' + filename)

    def _prepare_multiline_status(self, lines=1):
        self._progress = ProgressReporter(
            self.ydl, 'download', lines=lines,
            newline=bool(self.params.get('progress_with_newline')),
            preserve=not self.params.get('quiet'),
            disabled=bool(self.params.get('noprogress')),
            templates=self.params.get('progress_template', {}))

    def report_progress(self, s):
        self._progress.report_progress(s)

    def report_resuming_byte(self, resume_len):
        """Report attempt to resume at given byte."""
        self.to_screen('[download] Resuming download at byte %s' % resume_len)

    def report_retry(self, err, count, retries, frag_index=NO_DEFAULT, fatal=True):
        """Report retry"""
        is_frag = False if frag_index is NO_DEFAULT else 'fragment'
        RetryManager.report_retry(
            err, count, retries, info=self.to_screen,
            warn=lambda msg: self.to_screen(f'[download] Got error: {msg}'),
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
                self._progress.close()
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
        self._progress.close()
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

        str_args = [decodeArgument(a) for a in args]

        if exe is None:
            exe = os.path.basename(str_args[0])

        self.write_debug(f'{exe} command line: {shell_quote(str_args)}')
