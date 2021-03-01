from __future__ import division, unicode_literals

import os
import time
import json

from .common import FileDownloader
from .http import HttpFD
from ..utils import (
    error_to_compat_str,
    encodeFilename,
    sanitize_open,
    sanitized_Request,
)


class HttpQuietDownloader(HttpFD):
    def to_screen(self, *args, **kargs):
        pass


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
        self.to_screen(
            '[download] Got server HTTP error: %s. Retrying fragment %d (attempt %d of %s) ...'
            % (error_to_compat_str(err), frag_index, count, self.format_retries(retries)))

    def report_skip_fragment(self, frag_index):
        self.to_screen('[download] Skipping fragment %d ...' % frag_index)

    def _prepare_url(self, info_dict, url):
        headers = info_dict.get('http_headers')
        return sanitized_Request(url, None, headers) if headers else url

    def _prepare_and_start_frag_download(self, ctx):
        self._prepare_frag_download(ctx)
        self._start_frag_download(ctx)

    @staticmethod
    def __do_ytdl_file(ctx):
        return not ctx['live'] and not ctx['tmpfilename'] == '-'

    def _read_ytdl_file(self, ctx):
        assert 'ytdl_corrupt' not in ctx
        stream, _ = sanitize_open(self.ytdl_filename(ctx['filename']), 'r')
        try:
            ctx['fragment_index'] = json.loads(stream.read())['downloader']['current_fragment']['index']
        except Exception:
            ctx['ytdl_corrupt'] = True
        finally:
            stream.close()

    def _write_ytdl_file(self, ctx):
        frag_index_stream, _ = sanitize_open(self.ytdl_filename(ctx['filename']), 'w')
        downloader = {
            'current_fragment': {
                'index': ctx['fragment_index'],
            },
        }
        if ctx.get('fragment_count') is not None:
            downloader['fragment_count'] = ctx['fragment_count']
        frag_index_stream.write(json.dumps({'downloader': downloader}))
        frag_index_stream.close()

    def _download_fragment(self, ctx, frag_url, info_dict, headers=None, request_data=None):
        fragment_filename = '%s-Frag%d' % (ctx['tmpfilename'], ctx['fragment_index'])
        fragment_info_dict = {
            'url': frag_url,
            'http_headers': headers or info_dict.get('http_headers'),
            'request_data': request_data,
        }
        success = ctx['dl'].download(fragment_filename, fragment_info_dict)
        if not success:
            return False, None
        if fragment_info_dict.get('filetime'):
            ctx['fragment_filetime'] = fragment_info_dict.get('filetime')
        down, frag_sanitized = sanitize_open(fragment_filename, 'rb')
        ctx['fragment_filename_sanitized'] = frag_sanitized
        frag_content = down.read()
        down.close()
        return True, frag_content

    def _append_fragment(self, ctx, frag_content):
        try:
            ctx['dest_stream'].write(frag_content)
            ctx['dest_stream'].flush()
        finally:
            if self.__do_ytdl_file(ctx):
                self._write_ytdl_file(ctx)
            if not self.params.get('keep_fragments', False):
                os.remove(encodeFilename(ctx['fragment_filename_sanitized']))
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
        self.to_screen(
            '[%s] Total fragments: %s' % (self.FD_NAME, total_frags_str))
        self.report_destination(ctx['filename'])
        dl = HttpQuietDownloader(
            self.ydl,
            {
                'continuedl': True,
                'quiet': True,
                'noprogress': True,
                'ratelimit': self.params.get('ratelimit'),
                'retries': self.params.get('retries', 0),
                'nopart': self.params.get('nopart', False),
                'test': self.params.get('test', False),
            }
        )
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

        dest_stream, tmpfilename = sanitize_open(tmpfilename, open_mode)

        ctx.update({
            'dl': dl,
            'dest_stream': dest_stream,
            'tmpfilename': tmpfilename,
            # Total complete fragments downloaded so far in bytes
            'complete_frags_downloaded_bytes': resume_len,
        })

    def _start_frag_download(self, ctx):
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

        start = time.time()
        ctx.update({
            'started': start,
            # Amount of fragment's bytes downloaded by the time of the previous
            # frag progress hook invocation
            'prev_frag_downloaded_bytes': 0,
        })

        def frag_progress_hook(s):
            if s['status'] not in ('downloading', 'finished'):
                return

            time_now = time.time()
            state['elapsed'] = time_now - start
            frag_total_bytes = s.get('total_bytes') or 0
            if not ctx['live']:
                estimated_size = (
                    (ctx['complete_frags_downloaded_bytes'] + frag_total_bytes)
                    / (state['fragment_index'] + 1) * total_frags)
                state['total_bytes_estimate'] = estimated_size

            if s['status'] == 'finished':
                state['fragment_index'] += 1
                ctx['fragment_index'] = state['fragment_index']
                state['downloaded_bytes'] += frag_total_bytes - ctx['prev_frag_downloaded_bytes']
                ctx['complete_frags_downloaded_bytes'] = state['downloaded_bytes']
                ctx['prev_frag_downloaded_bytes'] = 0
            else:
                frag_downloaded_bytes = s['downloaded_bytes']
                state['downloaded_bytes'] += frag_downloaded_bytes - ctx['prev_frag_downloaded_bytes']
                if not ctx['live']:
                    state['eta'] = self.calc_eta(
                        start, time_now, estimated_size - resume_len,
                        state['downloaded_bytes'] - resume_len)
                state['speed'] = s.get('speed') or ctx.get('speed')
                ctx['speed'] = state['speed']
                ctx['prev_frag_downloaded_bytes'] = frag_downloaded_bytes
            self._hook_progress(state)

        ctx['dl'].add_progress_hook(frag_progress_hook)

        return start

    def _finish_frag_download(self, ctx):
        ctx['dest_stream'].close()
        if self.__do_ytdl_file(ctx):
            ytdl_filename = encodeFilename(self.ytdl_filename(ctx['filename']))
            if os.path.isfile(ytdl_filename):
                os.remove(ytdl_filename)
        elapsed = time.time() - ctx['started']

        if ctx['tmpfilename'] == '-':
            downloaded_bytes = ctx['complete_frags_downloaded_bytes']
        else:
            self.try_rename(ctx['tmpfilename'], ctx['filename'])
            if self.params.get('updatetime', True):
                filetime = ctx.get('fragment_filetime')
                if filetime:
                    try:
                        os.utime(ctx['filename'], (time.time(), filetime))
                    except Exception:
                        pass
            downloaded_bytes = os.path.getsize(encodeFilename(ctx['filename']))

        self._hook_progress({
            'downloaded_bytes': downloaded_bytes,
            'total_bytes': downloaded_bytes,
            'filename': ctx['filename'],
            'status': 'finished',
            'elapsed': elapsed,
        })

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
        self.to_screen(
            '[%s] Total fragments: %s' % (self.FD_NAME, total_frags_str))

        tmpfilename = self.temp_name(ctx['filename'])

        # Should be initialized before ytdl file check
        ctx.update({
            'tmpfilename': tmpfilename,
            'fragment_index': 0,
        })
