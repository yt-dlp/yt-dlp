import concurrent.futures
import contextlib
import http.client
import json
import math
import os
import struct
import threading
import time
import urllib.error
from bisect import bisect

from .common import FileDownloader
from .http import HttpFD
from ..aes import aes_cbc_decrypt_bytes, unpad_pkcs7
from ..compat import compat_os_name
from ..utils import (
    DownloadError,
    RetryManager,
    encodeFilename,
    sanitized_Request,
    traverse_obj,
)


class Timer:
    TIMER_FUNC = time.monotonic

    def __init__(self):
        self._last_ts = self.TIMER_FUNC()

    def elapsed_seconds(self) -> float:
        return self.TIMER_FUNC() - self._last_ts

    def has_elapsed(self, seconds: float) -> bool:
        assert seconds > 0.0
        elapsed_seconds = self.elapsed_seconds()
        if elapsed_seconds < seconds:
            return False

        self._last_ts += elapsed_seconds - elapsed_seconds % seconds
        return True


class SpeedometerMA:
    TIMER_FUNC = time.monotonic
    UPDATE_TIMESPAN_S = 1.0
    AVERAGE_TIMESPAN_S = 5.0

    def __init__(self, initial_bytes=0):
        self.ts_data = [(self.TIMER_FUNC(), initial_bytes)]
        self.timer = Timer()
        self.last_value = None

    def __call__(self, byte_counter):
        time_now = self.TIMER_FUNC()

        # only append data older than 50ms
        if time_now - self.ts_data[-1][0] > 0.05:
            self.ts_data.append((time_now, byte_counter))

        # remove older entries
        idx = max(0, bisect(self.ts_data, (time_now - self.AVERAGE_TIMESPAN_S, )) - 1)
        self.ts_data[0:idx] = ()

        diff_time = time_now - self.ts_data[0][0]
        speed = (byte_counter - self.ts_data[0][1]) / diff_time if diff_time else None
        if self.timer.has_elapsed(seconds=self.UPDATE_TIMESPAN_S):
            self.last_value = speed

        return self.last_value or speed


class SmoothETA:
    def __init__(self):
        self.last_value = None

    def __call__(self, value):
        if value <= 0:
            return 0

        time_now = time.monotonic()
        if self.last_value:
            predicted = self.last_value - time_now
            if predicted <= 0:
                deviation = float('inf')
            else:
                deviation = max(predicted, value) / min(predicted, value)

            if deviation < 1.25:
                return predicted

        self.last_value = time_now + value
        return value


class HttpQuietDownloader(HttpFD):
    def to_screen(self, *args, **kargs):
        pass

    to_console_title = to_screen


class FragmentFD(FileDownloader):
    """
    A base file downloader class for fragmented media (e.g. f4m/m3u8 manifests).

    Available options:

    fragment_retries:   Number of times to retry a fragment for HTTP error (DASH
                        and hlsnative only)
    skip_unavailable_fragments:
                        Skip unavailable fragments (DASH and hlsnative only)
    keep_fragments:     Keep downloaded fragments on disk after downloading is
                        finished
    concurrent_fragment_downloads:  The number of threads to use for native hls and dash downloads
    _no_ytdl_file:      Don't use .ytdl file

    For each incomplete fragment download yt-dlp keeps on disk a special
    bookkeeping file with download state and metadata (in future such files will
    be used for any incomplete download handled by yt-dlp). This file is
    used to properly handle resuming, check download file consistency and detect
    potential errors. The file has a .ytdl extension and represents a standard
    JSON file of the following format:

    extractor:
        Dictionary of extractor related data. TBD.

    downloader:
        Dictionary of downloader related data. May contain following data:
            current_fragment:
                Dictionary with current (being downloaded) fragment data:
                index:  0-based index of current fragment among all fragments
            fragment_count:
                Total count of fragments

    This feature is experimental and file format may change in future.
    """

    def report_retry_fragment(self, err, frag_index, count, retries):
        self.deprecation_warning('yt_dlp.downloader.FragmentFD.report_retry_fragment is deprecated. '
                                 'Use yt_dlp.downloader.FileDownloader.report_retry instead')
        return self.report_retry(err, count, retries, frag_index)

    def report_skip_fragment(self, frag_index, err=None):
        err = f' {err};' if err else ''
        self.to_screen(f'[download]{err} Skipping fragment {frag_index:d} ...')

    def _prepare_url(self, info_dict, url):
        headers = info_dict.get('http_headers')
        return sanitized_Request(url, None, headers) if headers else url

    def _prepare_and_start_frag_download(self, ctx, info_dict):
        self._prepare_frag_download(ctx)
        self._start_frag_download(ctx, info_dict)

    def __do_ytdl_file(self, ctx):
        return ctx['live'] is not True and ctx['tmpfilename'] != '-' and not self.params.get('_no_ytdl_file')

    def _read_ytdl_file(self, ctx):
        assert 'ytdl_corrupt' not in ctx
        stream, _ = self.sanitize_open(self.ytdl_filename(ctx['filename']), 'r')
        try:
            ytdl_data = json.loads(stream.read())
            ctx['fragment_index'] = ytdl_data['downloader']['current_fragment']['index']
            if 'extra_state' in ytdl_data['downloader']:
                ctx['extra_state'] = ytdl_data['downloader']['extra_state']
        except Exception:
            ctx['ytdl_corrupt'] = True
        finally:
            stream.close()

    def _write_ytdl_file(self, ctx):
        frag_index_stream, _ = self.sanitize_open(self.ytdl_filename(ctx['filename']), 'w')
        try:
            downloader = {
                'current_fragment': {
                    'index': ctx['fragment_index'],
                },
            }
            if 'extra_state' in ctx:
                downloader['extra_state'] = ctx['extra_state']
            if ctx.get('fragment_count') is not None:
                downloader['fragment_count'] = ctx['fragment_count']
            frag_index_stream.write(json.dumps({'downloader': downloader}))
        finally:
            frag_index_stream.close()

    def _download_fragment(self, ctx, frag_url, info_dict, headers=None, request_data=None):
        fragment_filename = '%s-Frag%d' % (ctx['tmpfilename'], ctx['fragment_index'])
        fragment_info_dict = {
            'url': frag_url,
            'http_headers': headers or info_dict.get('http_headers'),
            'request_data': request_data,
        }
        success, _ = ctx['dl'].download(fragment_filename, fragment_info_dict)
        if not success:
            return False
        if fragment_info_dict.get('filetime'):
            ctx['fragment_filetime'] = fragment_info_dict.get('filetime')
        ctx['fragment_filename_sanitized'] = fragment_filename
        return True

    def _read_fragment(self, ctx):
        if not ctx.get('fragment_filename_sanitized'):
            return None
        try:
            down, frag_sanitized = self.sanitize_open(ctx['fragment_filename_sanitized'], 'rb')
        except FileNotFoundError:
            if ctx.get('live'):
                return None
            raise
        ctx['fragment_filename_sanitized'] = frag_sanitized
        frag_content = down.read()
        down.close()
        return frag_content

    def _append_fragment(self, ctx, frag_content):
        try:
            ctx['dest_stream'].write(frag_content)
            ctx['dest_stream'].flush()
        finally:
            if self.__do_ytdl_file(ctx):
                self._write_ytdl_file(ctx)
            if not self.params.get('keep_fragments', False):
                self.try_remove(encodeFilename(ctx['fragment_filename_sanitized']))
            del ctx['fragment_filename_sanitized']

    def _prepare_frag_download(self, ctx):
        if 'live' not in ctx:
            ctx['live'] = False
        if not ctx['live']:
            total_frags_str = '%d' % ctx['total_frags']
            ad_frags = ctx.get('ad_frags', 0)
            if ad_frags:
                total_frags_str += ' (not including %d ad)' % ad_frags
        else:
            total_frags_str = 'unknown (live)'
        self.to_screen(f'[{self.FD_NAME}] Total fragments: {total_frags_str}')
        self.report_destination(ctx['filename'])
        dl = HttpQuietDownloader(self.ydl, {
            **self.params,
            'noprogress': True,
            'test': False,
        })
        tmpfilename = self.temp_name(ctx['filename'])
        open_mode = 'wb'
        resume_len = 0

        # Establish possible resume length
        if os.path.isfile(encodeFilename(tmpfilename)):
            open_mode = 'ab'
            resume_len = os.path.getsize(encodeFilename(tmpfilename))

        # Should be initialized before ytdl file check
        ctx.update({
            'tmpfilename': tmpfilename,
            'fragment_index': 0,
        })

        if self.__do_ytdl_file(ctx):
            if os.path.isfile(encodeFilename(self.ytdl_filename(ctx['filename']))):
                self._read_ytdl_file(ctx)
                is_corrupt = ctx.get('ytdl_corrupt') is True
                is_inconsistent = ctx['fragment_index'] > 0 and resume_len == 0
                if is_corrupt or is_inconsistent:
                    message = (
                        '.ytdl file is corrupt' if is_corrupt else
                        'Inconsistent state of incomplete fragment download')
                    self.report_warning(
                        '%s. Restarting from the beginning ...' % message)
                    ctx['fragment_index'] = resume_len = 0
                    if 'ytdl_corrupt' in ctx:
                        del ctx['ytdl_corrupt']
                    self._write_ytdl_file(ctx)
            else:
                self._write_ytdl_file(ctx)
                assert ctx['fragment_index'] == 0

        dest_stream, tmpfilename = self.sanitize_open(tmpfilename, open_mode)

        ctx.update({
            'dl': dl,
            'dest_stream': dest_stream,
            'tmpfilename': tmpfilename,
            # Total complete fragments downloaded so far in bytes
            'complete_frags_downloaded_bytes': resume_len,
        })

    def _start_frag_download(self, ctx, info_dict):
        def with_thread_lock(func):
            """ this decorator makes a function thread-safe """
            lock = threading.Lock()

            def locked_func(*args, **kwargs):
                with lock:
                    return func(*args, **kwargs)
            return locked_func

        resume_len = ctx['complete_frags_downloaded_bytes']
        total_frags = ctx['total_frags']

        # This dict stores the download progress, it's updated by the progress
        # hook
        state = {
            'status': 'downloading',
            'downloaded_bytes': resume_len,
            'fragment_index': ctx['fragment_index'],
            'fragment_count': total_frags,
            'filename': ctx['filename'],
            'tmpfilename': ctx['tmpfilename'],
        }

        ctx['started'] = start = time.time()
        speedometer = SpeedometerMA(initial_bytes=resume_len)
        progress_timer = Timer()
        smooth_eta = SmoothETA()

        # contains the returned info from active threads
        fragments_map = {}

        @with_thread_lock
        def frag_progress_hook(s):
            if not (s['status'] in ('downloading', 'finished')
                    and 'downloaded_bytes' in s and 'total_bytes' in s):
                return

            pending_fragments = 0
            pending_total_bytes = 0
            pending_downloaded_bytes = 0
            fragments_map[threading.get_ident()] = s

            for thread_id, info in tuple(fragments_map.items()):
                if info['status'] == 'finished':
                    ctx['complete_frags_downloaded_bytes'] += info['downloaded_bytes']
                    state['fragment_index'] += 1
                    del fragments_map[thread_id]
                elif info['status'] == 'downloading':
                    pending_fragments += 1
                    pending_downloaded_bytes += info['downloaded_bytes'] or 0
                    pending_total_bytes += info['total_bytes'] or 0

            state['downloaded_bytes'] = (
                ctx['complete_frags_downloaded_bytes'] + pending_downloaded_bytes)

            if total_frags:
                state['total_bytes_estimate'] = (
                    (ctx['complete_frags_downloaded_bytes'] + pending_total_bytes)
                    / (state['fragment_index'] + pending_fragments) * total_frags
                )
            else:
                state['total_bytes_estimate'] = None
                state['fragment_count'] = ctx.get('fragment_count')

            if state['fragment_index'] == total_frags:
                state['status'] = 'finished'

            state['max_progress'] = ctx.get('max_progress')
            state['progress_idx'] = ctx.get('progress_idx')
            state['speed'] = speedometer(state['downloaded_bytes'])
            state['elapsed'] = time.time() - start

            if progress_timer.has_elapsed(seconds=0.1) or state['status'] == 'finished':
                if state.get('speed') and state.get('total_bytes_estimate'):
                    state['eta'] = smooth_eta(
                        (state['total_bytes_estimate'] - state['downloaded_bytes']) / state['speed'])
                self._hook_progress(state, info_dict)

        ctx['dl'].add_progress_hook(frag_progress_hook)

        return start

    def _finish_frag_download(self, ctx, info_dict):
        ctx['dest_stream'].close()
        if self.__do_ytdl_file(ctx):
            ytdl_filename = encodeFilename(self.ytdl_filename(ctx['filename']))
            if os.path.isfile(ytdl_filename):
                self.try_remove(ytdl_filename)
        elapsed = time.time() - ctx['started']

        if ctx['tmpfilename'] == '-':
            downloaded_bytes = ctx['complete_frags_downloaded_bytes']
        else:
            self.try_rename(ctx['tmpfilename'], ctx['filename'])
            if self.params.get('updatetime', True):
                filetime = ctx.get('fragment_filetime')
                if filetime:
                    with contextlib.suppress(Exception):
                        os.utime(ctx['filename'], (time.time(), filetime))
            downloaded_bytes = os.path.getsize(encodeFilename(ctx['filename']))

        self._hook_progress({
            'downloaded_bytes': downloaded_bytes,
            'total_bytes': downloaded_bytes,
            'filename': ctx['filename'],
            'status': 'finished',
            'elapsed': elapsed,
            'max_progress': ctx.get('max_progress'),
            'progress_idx': ctx.get('progress_idx'),
        }, info_dict)

    def _prepare_external_frag_download(self, ctx):
        if 'live' not in ctx:
            ctx['live'] = False
        if not ctx['live']:
            total_frags_str = '%d' % ctx['total_frags']
            ad_frags = ctx.get('ad_frags', 0)
            if ad_frags:
                total_frags_str += ' (not including %d ad)' % ad_frags
        else:
            total_frags_str = 'unknown (live)'
        self.to_screen(f'[{self.FD_NAME}] Total fragments: {total_frags_str}')

        tmpfilename = self.temp_name(ctx['filename'])

        # Should be initialized before ytdl file check
        ctx.update({
            'tmpfilename': tmpfilename,
            'fragment_index': 0,
        })

    def decrypter(self, info_dict):
        _key_cache = {}

        def _get_key(url):
            if url not in _key_cache:
                _key_cache[url] = self.ydl.urlopen(self._prepare_url(info_dict, url)).read()
            return _key_cache[url]

        def decrypt_fragment(fragment, frag_content):
            if frag_content is None:
                return
            decrypt_info = fragment.get('decrypt_info')
            if not decrypt_info or decrypt_info['METHOD'] != 'AES-128':
                return frag_content
            iv = decrypt_info.get('IV') or struct.pack('>8xq', fragment['media_sequence'])
            decrypt_info['KEY'] = decrypt_info.get('KEY') or _get_key(info_dict.get('_decryption_key_url') or decrypt_info['URI'])
            # Don't decrypt the content in tests since the data is explicitly truncated and it's not to a valid block
            # size (see https://github.com/ytdl-org/youtube-dl/pull/27660). Tests only care that the correct data downloaded,
            # not what it decrypts to.
            if self.params.get('test', False):
                return frag_content
            return unpad_pkcs7(aes_cbc_decrypt_bytes(frag_content, decrypt_info['KEY'], iv))

        return decrypt_fragment

    def download_and_append_fragments_multiple(self, *args, pack_func=None, finish_func=None):
        '''
        @params (ctx1, fragments1, info_dict1), (ctx2, fragments2, info_dict2), ...
                all args must be either tuple or list
        '''
        interrupt_trigger = [True]
        max_progress = len(args)
        if max_progress == 1:
            return self.download_and_append_fragments(*args[0], pack_func=pack_func, finish_func=finish_func)
        max_workers = self.params.get('concurrent_fragment_downloads', 1)
        if max_progress > 1:
            self._prepare_multiline_status(max_progress)
        is_live = any(traverse_obj(args, (..., 2, 'is_live'), default=[]))

        def thread_func(idx, ctx, fragments, info_dict, tpe):
            ctx['max_progress'] = max_progress
            ctx['progress_idx'] = idx
            return self.download_and_append_fragments(
                ctx, fragments, info_dict, pack_func=pack_func, finish_func=finish_func,
                tpe=tpe, interrupt_trigger=interrupt_trigger)

        class FTPE(concurrent.futures.ThreadPoolExecutor):
            # has to stop this or it's going to wait on the worker thread itself
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        if compat_os_name == 'nt':
            def future_result(future):
                while True:
                    try:
                        return future.result(0.1)
                    except KeyboardInterrupt:
                        raise
                    except concurrent.futures.TimeoutError:
                        continue
        else:
            def future_result(future):
                return future.result()

        def interrupt_trigger_iter(fg):
            for f in fg:
                if not interrupt_trigger[0]:
                    break
                yield f

        spins = []
        for idx, (ctx, fragments, info_dict) in enumerate(args):
            tpe = FTPE(math.ceil(max_workers / max_progress))
            job = tpe.submit(thread_func, idx, ctx, interrupt_trigger_iter(fragments), info_dict, tpe)
            spins.append((tpe, job))

        result = True
        for tpe, job in spins:
            try:
                result = result and future_result(job)
            except KeyboardInterrupt:
                interrupt_trigger[0] = False
            finally:
                tpe.shutdown(wait=True)
        if not interrupt_trigger[0] and not is_live:
            raise KeyboardInterrupt()
        # we expect the user wants to stop and DO WANT the preceding postprocessors to run;
        # so returning a intermediate result here instead of KeyboardInterrupt on live
        return result

    def download_and_append_fragments(
            self, ctx, fragments, info_dict, *, pack_func=None, finish_func=None,
            tpe=None, interrupt_trigger=None):
        if not interrupt_trigger:
            interrupt_trigger = (True, )

        is_fatal = (
            ((lambda _: False) if info_dict.get('is_live') else (lambda idx: idx == 0))
            if self.params.get('skip_unavailable_fragments', True) else (lambda _: True))

        if not pack_func:
            pack_func = lambda frag_content, _: frag_content

        def download_fragment(fragment, ctx):
            if not interrupt_trigger[0]:
                return

            frag_index = ctx['fragment_index'] = fragment['frag_index']
            ctx['last_error'] = None
            headers = info_dict.get('http_headers', {}).copy()
            byte_range = fragment.get('byte_range')
            if byte_range:
                headers['Range'] = 'bytes=%d-%d' % (byte_range['start'], byte_range['end'] - 1)

            # Never skip the first fragment
            fatal = is_fatal(fragment.get('index') or (frag_index - 1))

            def error_callback(err, count, retries):
                if fatal and count > retries:
                    ctx['dest_stream'].close()
                self.report_retry(err, count, retries, frag_index, fatal)
                ctx['last_error'] = err

            for retry in RetryManager(self.params.get('fragment_retries'), error_callback):
                try:
                    ctx['fragment_count'] = fragment.get('fragment_count')
                    if not self._download_fragment(ctx, fragment['url'], info_dict, headers):
                        return
                except (urllib.error.HTTPError, http.client.IncompleteRead) as err:
                    retry.error = err
                    continue
                except DownloadError:  # has own retry settings
                    if fatal:
                        raise

        def append_fragment(frag_content, frag_index, ctx):
            if frag_content:
                self._append_fragment(ctx, pack_func(frag_content, frag_index))
            elif not is_fatal(frag_index - 1):
                self.report_skip_fragment(frag_index, 'fragment not found')
            else:
                ctx['dest_stream'].close()
                self.report_error(f'fragment {frag_index} not found, unable to continue')
                return False
            return True

        decrypt_fragment = self.decrypter(info_dict)

        max_workers = math.ceil(
            self.params.get('concurrent_fragment_downloads', 1) / ctx.get('max_progress', 1))
        if max_workers > 1:
            def _download_fragment(fragment):
                ctx_copy = ctx.copy()
                download_fragment(fragment, ctx_copy)
                return fragment, fragment['frag_index'], ctx_copy.get('fragment_filename_sanitized')

            with tpe or concurrent.futures.ThreadPoolExecutor(max_workers) as pool:
                try:
                    for fragment, frag_index, frag_filename in pool.map(_download_fragment, fragments):
                        ctx.update({
                            'fragment_filename_sanitized': frag_filename,
                            'fragment_index': frag_index,
                        })
                        if not append_fragment(decrypt_fragment(fragment, self._read_fragment(ctx)), frag_index, ctx):
                            return False
                except KeyboardInterrupt:
                    self._finish_multiline_status()
                    self.report_error(
                        'Interrupted by user. Waiting for all threads to shutdown...', is_error=False, tb=False)
                    pool.shutdown(wait=False)
                    raise
        else:
            for fragment in fragments:
                if not interrupt_trigger[0]:
                    break
                try:
                    download_fragment(fragment, ctx)
                    result = append_fragment(
                        decrypt_fragment(fragment, self._read_fragment(ctx)), fragment['frag_index'], ctx)
                except KeyboardInterrupt:
                    if info_dict.get('is_live'):
                        break
                    raise
                if not result:
                    return False

        if finish_func is not None:
            ctx['dest_stream'].write(finish_func())
            ctx['dest_stream'].flush()
        self._finish_frag_download(ctx, info_dict)
        return True
