import os
import random
import time

from .common import FileDownloader
from ..networking import Request
from ..networking.exceptions import (
    CertificateVerifyError,
    HTTPError,
    TransportError,
)
from ..utils import (
    ContentTooShortError,
    RetryManager,
    ThrottledDownload,
    XAttrMetadataError,
    XAttrUnavailableError,
    encodeFilename,
    int_or_none,
    parse_http_range,
    try_call,
    write_xattr,
)
from ..utils.networking import HTTPHeaderDict


class HttpFD(FileDownloader):
    def real_download(self, filename, info_dict):
        url = info_dict['url']
        request_data = info_dict.get('request_data', None)

        class DownloadContext(dict):
            __getattr__ = dict.get
            __setattr__ = dict.__setitem__
            __delattr__ = dict.__delitem__

        ctx = DownloadContext()
        ctx.filename = filename
        ctx.tmpfilename = self.temp_name(filename)
        ctx.stream = None

        # Disable compression
        headers = HTTPHeaderDict({'Accept-Encoding': 'identity'}, info_dict.get('http_headers'))

        is_test = self.params.get('test', False)
        chunk_size = self._TEST_FILE_SIZE if is_test else (
            self.params.get('http_chunk_size')
            or info_dict.get('downloader_options', {}).get('http_chunk_size')
            or 0)

        ctx.open_mode = 'wb'
        ctx.resume_len = 0
        ctx.block_size = self.params.get('buffersize', 1024)
        ctx.start_time = time.time()

        # parse given Range
        req_start, req_end, _ = parse_http_range(headers.get('Range'))

        if self.params.get('continuedl', True):
            # Establish possible resume length
            if os.path.isfile(encodeFilename(ctx.tmpfilename)):
                ctx.resume_len = os.path.getsize(
                    encodeFilename(ctx.tmpfilename))

        ctx.is_resume = ctx.resume_len > 0

        class SucceedDownload(Exception):
            pass

        class RetryDownload(Exception):
            def __init__(self, source_error):
                self.source_error = source_error

        class NextFragment(Exception):
            pass

        def establish_connection():
            ctx.chunk_size = (random.randint(int(chunk_size * 0.95), chunk_size)
                              if not is_test and chunk_size else chunk_size)
            if ctx.resume_len > 0:
                range_start = ctx.resume_len
                if req_start is not None:
                    # offset the beginning of Range to be within request
                    range_start += req_start
                if ctx.is_resume:
                    self.report_resuming_byte(ctx.resume_len)
                ctx.open_mode = 'ab'
            elif req_start is not None:
                range_start = req_start
            elif ctx.chunk_size > 0:
                range_start = 0
            else:
                range_start = None
            ctx.is_resume = False

            if ctx.chunk_size:
                chunk_aware_end = range_start + ctx.chunk_size - 1
                # we're not allowed to download outside Range
                range_end = chunk_aware_end if req_end is None else min(chunk_aware_end, req_end)
            elif req_end is not None:
                # there's no need for chunked downloads, so download until the end of Range
                range_end = req_end
            else:
                range_end = None

            if try_call(lambda: range_start > range_end):
                ctx.resume_len = 0
                ctx.open_mode = 'wb'
                raise RetryDownload(Exception(f'Conflicting range. (start={range_start} > end={range_end})'))

            if try_call(lambda: range_end >= ctx.content_len):
                range_end = ctx.content_len - 1

            request = Request(url, request_data, headers)
            has_range = range_start is not None
            if has_range:
                request.headers['Range'] = f'bytes={int(range_start)}-{int_or_none(range_end) or ""}'
            # Establish connection
            try:
                ctx.data = self.ydl.urlopen(request)
                # When trying to resume, Content-Range HTTP header of response has to be checked
                # to match the value of requested Range HTTP header. This is due to a webservers
                # that don't support resuming and serve a whole file with no Content-Range
                # set in response despite of requested Range (see
                # https://github.com/ytdl-org/youtube-dl/issues/6057#issuecomment-126129799)
                if has_range:
                    content_range = ctx.data.headers.get('Content-Range')
                    content_range_start, content_range_end, content_len = parse_http_range(content_range)
                    # Content-Range is present and matches requested Range, resume is possible
                    if range_start == content_range_start and (
                            # Non-chunked download
                            not ctx.chunk_size
                            # Chunked download and requested piece or
                            # its part is promised to be served
                            or content_range_end == range_end
                            or content_len < range_end):
                        ctx.content_len = content_len
                        if content_len or req_end:
                            ctx.data_len = min(content_len or req_end, req_end or content_len) - (req_start or 0)
                        return
                    # Content-Range is either not present or invalid. Assuming remote webserver is
                    # trying to send the whole file, resume is not possible, so wiping the local file
                    # and performing entire redownload
                    elif range_start > 0:
                        self.report_unable_to_resume()
                    ctx.resume_len = 0
                    ctx.open_mode = 'wb'
                ctx.data_len = ctx.content_len = int_or_none(ctx.data.headers.get('Content-length', None))
            except HTTPError as err:
                if err.status == 416:
                    # Unable to resume (requested range not satisfiable)
                    try:
                        # Open the connection again without the range header
                        ctx.data = self.ydl.urlopen(
                            Request(url, request_data, headers))
                        content_length = ctx.data.headers['Content-Length']
                    except HTTPError as err:
                        if err.status < 500 or err.status >= 600:
                            raise
                    else:
                        # Examine the reported length
                        if (content_length is not None
                                and (ctx.resume_len - 100 < int(content_length) < ctx.resume_len + 100)):
                            # The file had already been fully downloaded.
                            # Explanation to the above condition: in issue #175 it was revealed that
                            # YouTube sometimes adds or removes a few bytes from the end of the file,
                            # changing the file size slightly and causing problems for some users. So
                            # I decided to implement a suggested change and consider the file
                            # completely downloaded if the file size differs less than 100 bytes from
                            # the one in the hard drive.
                            self.report_file_already_downloaded(ctx.filename)
                            self.try_rename(ctx.tmpfilename, ctx.filename)
                            self._hook_progress({
                                'filename': ctx.filename,
                                'status': 'finished',
                                'downloaded_bytes': ctx.resume_len,
                                'total_bytes': ctx.resume_len,
                            }, info_dict)
                            raise SucceedDownload()
                        else:
                            # The length does not match, we start the download over
                            self.report_unable_to_resume()
                            ctx.resume_len = 0
                            ctx.open_mode = 'wb'
                            return
                elif err.status < 500 or err.status >= 600:
                    # Unexpected HTTP error
                    raise
                raise RetryDownload(err)
            except CertificateVerifyError:
                raise
            except TransportError as err:
                raise RetryDownload(err)

        def close_stream():
            if ctx.stream is not None:
                if not ctx.tmpfilename == '-':
                    ctx.stream.close()
                ctx.stream = None

        def download():
            data_len = ctx.data.headers.get('Content-length')

            if ctx.data.headers.get('Content-encoding'):
                # Content-encoding is present, Content-length is not reliable anymore as we are
                # doing auto decompression. (See: https://github.com/yt-dlp/yt-dlp/pull/6176)
                data_len = None

            # Range HTTP header may be ignored/unsupported by a webserver
            # (e.g. extractor/scivee.py, extractor/bambuser.py).
            # However, for a test we still would like to download just a piece of a file.
            # To achieve this we limit data_len to _TEST_FILE_SIZE and manually control
            # block size when downloading a file.
            if is_test and (data_len is None or int(data_len) > self._TEST_FILE_SIZE):
                data_len = self._TEST_FILE_SIZE

            if data_len is not None:
                data_len = int(data_len) + ctx.resume_len
                min_data_len = self.params.get('min_filesize')
                max_data_len = self.params.get('max_filesize')
                if min_data_len is not None and data_len < min_data_len:
                    self.to_screen(
                        f'\r[download] File is smaller than min-filesize ({data_len} bytes < {min_data_len} bytes). Aborting.')
                    return False
                if max_data_len is not None and data_len > max_data_len:
                    self.to_screen(
                        f'\r[download] File is larger than max-filesize ({data_len} bytes > {max_data_len} bytes). Aborting.')
                    return False

            byte_counter = 0 + ctx.resume_len
            block_size = ctx.block_size
            start = time.time()

            # measure time over whole while-loop, so slow_down() and best_block_size() work together properly
            now = None  # needed for slow_down() in the first loop run
            before = start  # start measuring

            def retry(e):
                close_stream()
                if ctx.tmpfilename == '-':
                    ctx.resume_len = byte_counter
                else:
                    try:
                        ctx.resume_len = os.path.getsize(encodeFilename(ctx.tmpfilename))
                    except FileNotFoundError:
                        ctx.resume_len = 0
                raise RetryDownload(e)

            while True:
                try:
                    # Download and write
                    data_block = ctx.data.read(block_size if not is_test else min(block_size, data_len - byte_counter))
                except TransportError as err:
                    retry(err)

                byte_counter += len(data_block)

                # exit loop when download is finished
                if len(data_block) == 0:
                    break

                # Open destination file just in time
                if ctx.stream is None:
                    try:
                        ctx.stream, ctx.tmpfilename = self.sanitize_open(
                            ctx.tmpfilename, ctx.open_mode)
                        assert ctx.stream is not None
                        ctx.filename = self.undo_temp_name(ctx.tmpfilename)
                        self.report_destination(ctx.filename)
                    except OSError as err:
                        self.report_error('unable to open for writing: %s' % str(err))
                        return False

                    if self.params.get('xattr_set_filesize', False) and data_len is not None:
                        try:
                            write_xattr(ctx.tmpfilename, 'user.ytdl.filesize', str(data_len).encode())
                        except (XAttrUnavailableError, XAttrMetadataError) as err:
                            self.report_error('unable to set filesize xattr: %s' % str(err))

                try:
                    ctx.stream.write(data_block)
                except OSError as err:
                    self.to_stderr('\n')
                    self.report_error('unable to write data: %s' % str(err))
                    return False

                # Apply rate limit
                self.slow_down(start, now, byte_counter - ctx.resume_len)

                # end measuring of one loop run
                now = time.time()
                after = now

                # Adjust block size
                if not self.params.get('noresizebuffer', False):
                    block_size = self.best_block_size(after - before, len(data_block))

                before = after

                # Progress message
                speed = self.calc_speed(start, now, byte_counter - ctx.resume_len)
                if ctx.data_len is None:
                    eta = None
                else:
                    eta = self.calc_eta(start, time.time(), ctx.data_len - ctx.resume_len, byte_counter - ctx.resume_len)

                self._hook_progress({
                    'status': 'downloading',
                    'downloaded_bytes': byte_counter,
                    'total_bytes': ctx.data_len,
                    'tmpfilename': ctx.tmpfilename,
                    'filename': ctx.filename,
                    'eta': eta,
                    'speed': speed,
                    'elapsed': now - ctx.start_time,
                    'ctx_id': info_dict.get('ctx_id'),
                }, info_dict)

                if data_len is not None and byte_counter == data_len:
                    break

                if speed and speed < (self.params.get('throttledratelimit') or 0):
                    # The speed must stay below the limit for 3 seconds
                    # This prevents raising error when the speed temporarily goes down
                    if ctx.throttle_start is None:
                        ctx.throttle_start = now
                    elif now - ctx.throttle_start > 3:
                        if ctx.stream is not None and ctx.tmpfilename != '-':
                            ctx.stream.close()
                        raise ThrottledDownload()
                elif speed:
                    ctx.throttle_start = None

            if ctx.stream is None:
                self.to_stderr('\n')
                self.report_error('Did not get any data blocks')
                return False

            if not is_test and ctx.chunk_size and ctx.content_len is not None and byte_counter < ctx.content_len:
                ctx.resume_len = byte_counter
                raise NextFragment()

            if ctx.tmpfilename != '-':
                ctx.stream.close()

            if data_len is not None and byte_counter != data_len:
                err = ContentTooShortError(byte_counter, int(data_len))
                retry(err)

            self.try_rename(ctx.tmpfilename, ctx.filename)

            # Update file modification time
            if self.params.get('updatetime', True):
                info_dict['filetime'] = self.try_utime(ctx.filename, ctx.data.headers.get('last-modified', None))

            self._hook_progress({
                'downloaded_bytes': byte_counter,
                'total_bytes': byte_counter,
                'filename': ctx.filename,
                'status': 'finished',
                'elapsed': time.time() - ctx.start_time,
                'ctx_id': info_dict.get('ctx_id'),
            }, info_dict)

            return True

        for retry in RetryManager(self.params.get('retries'), self.report_retry):
            try:
                establish_connection()
                return download()
            except RetryDownload as err:
                retry.error = err.source_error
                continue
            except NextFragment:
                retry.error = None
                retry.attempt -= 1
                continue
            except SucceedDownload:
                return True
            except:  # noqa: E722
                close_stream()
                raise
        return False
