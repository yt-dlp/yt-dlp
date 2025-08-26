import enum
import functools
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid

from .fragment import FragmentFD
from ..networking import Request
from ..postprocessor.ffmpeg import EXT_TO_OUT_FORMATS, FFmpegPostProcessor
from ..utils import (
    Popen,
    RetryManager,
    _configuration_args,
    check_executable,
    classproperty,
    cli_bool_option,
    cli_option,
    cli_valueless_option,
    determine_ext,
    encodeArgument,
    find_available_port,
    remove_end,
    traverse_obj,
)


class Features(enum.Enum):
    TO_STDOUT = enum.auto()
    MULTIPLE_FORMATS = enum.auto()


class ExternalFD(FragmentFD):
    SUPPORTED_PROTOCOLS = ('http', 'https', 'ftp', 'ftps')
    SUPPORTED_FEATURES = ()
    _CAPTURE_STDERR = True

    def real_download(self, filename, info_dict):
        self.report_destination(filename)
        tmpfilename = self.temp_name(filename)
        self._cookies_tempfile = None

        try:
            started = time.time()
            retval = self._call_downloader(tmpfilename, info_dict)
        except KeyboardInterrupt:
            if not info_dict.get('is_live'):
                raise
            # Live stream downloading cancellation should be considered as
            # correct and expected termination thus all postprocessing
            # should take place
            retval = 0
            self.to_screen(f'[{self.get_basename()}] Interrupted by user')
        finally:
            if self._cookies_tempfile:
                self.try_remove(self._cookies_tempfile)

        if retval == 0:
            status = {
                'filename': filename,
                'status': 'finished',
                'elapsed': time.time() - started,
            }
            if filename != '-':
                fsize = os.path.getsize(tmpfilename)
                self.try_rename(tmpfilename, filename)
                status.update({
                    'downloaded_bytes': fsize,
                    'total_bytes': fsize,
                })
            self._hook_progress(status, info_dict)
            return True
        else:
            self.to_stderr('\n')
            self.report_error('%s exited with code %d' % (
                self.get_basename(), retval))
            return False

    @classmethod
    def get_basename(cls):
        return cls.__name__[:-2].lower()

    @classproperty
    def EXE_NAME(cls):
        return cls.get_basename()

    @functools.cached_property
    def exe(self):
        return self.EXE_NAME

    @classmethod
    def available(cls, path=None):
        path = check_executable(
            cls.EXE_NAME if path in (None, cls.get_basename()) else path,
            [cls.AVAILABLE_OPT])
        if not path:
            return False
        cls.exe = path
        return path

    @classmethod
    def supports(cls, info_dict):
        return all((
            not info_dict.get('to_stdout') or Features.TO_STDOUT in cls.SUPPORTED_FEATURES,
            '+' not in info_dict['protocol'] or Features.MULTIPLE_FORMATS in cls.SUPPORTED_FEATURES,
            not traverse_obj(info_dict, ('hls_aes', ...), 'extra_param_to_segment_url', 'extra_param_to_key_url'),
            all(proto in cls.SUPPORTED_PROTOCOLS for proto in info_dict['protocol'].split('+')),
        ))

    @classmethod
    def can_download(cls, info_dict, path=None):
        return cls.available(path) and cls.supports(info_dict)

    def _option(self, command_option, param):
        return cli_option(self.params, command_option, param)

    def _bool_option(self, command_option, param, true_value='true', false_value='false', separator=None):
        return cli_bool_option(self.params, command_option, param, true_value, false_value, separator)

    def _valueless_option(self, command_option, param, expected_value=True):
        return cli_valueless_option(self.params, command_option, param, expected_value)

    def _configuration_args(self, keys=None, *args, **kwargs):
        return _configuration_args(
            self.get_basename(), self.params.get('external_downloader_args'), self.EXE_NAME,
            keys, *args, **kwargs)

    def _write_cookies(self):
        if not self.ydl.cookiejar.filename:
            tmp_cookies = tempfile.NamedTemporaryFile(suffix='.cookies', delete=False)
            tmp_cookies.close()
            self._cookies_tempfile = tmp_cookies.name
            self.to_screen(f'[download] Writing temporary cookies file to "{self._cookies_tempfile}"')
        # real_download resets _cookies_tempfile; if it's None then save() will write to cookiejar.filename
        self.ydl.cookiejar.save(self._cookies_tempfile)
        return self.ydl.cookiejar.filename or self._cookies_tempfile

    def _call_downloader(self, tmpfilename, info_dict):
        """ Either overwrite this or implement _make_cmd """
        cmd = [encodeArgument(a) for a in self._make_cmd(tmpfilename, info_dict)]

        self._debug_cmd(cmd)

        if 'fragments' not in info_dict:
            _, stderr, returncode = self._call_process(cmd, info_dict)
            if returncode and stderr:
                self.to_stderr(stderr)
            return returncode

        skip_unavailable_fragments = self.params.get('skip_unavailable_fragments', True)

        retry_manager = RetryManager(self.params.get('fragment_retries'), self.report_retry,
                                     frag_index=None, fatal=not skip_unavailable_fragments)
        for retry in retry_manager:
            _, stderr, returncode = self._call_process(cmd, info_dict)
            if not returncode:
                break
            # TODO: Decide whether to retry based on error code
            # https://aria2.github.io/manual/en/html/aria2c.html#exit-status
            if stderr:
                self.to_stderr(stderr)
            retry.error = Exception()
            continue
        if not skip_unavailable_fragments and retry_manager.error:
            return -1

        decrypt_fragment = self.decrypter(info_dict)
        dest, _ = self.sanitize_open(tmpfilename, 'wb')
        for frag_index, fragment in enumerate(info_dict['fragments']):
            fragment_filename = f'{tmpfilename}-Frag{frag_index}'
            try:
                src, _ = self.sanitize_open(fragment_filename, 'rb')
            except OSError as err:
                if skip_unavailable_fragments and frag_index > 1:
                    self.report_skip_fragment(frag_index, err)
                    continue
                self.report_error(f'Unable to open fragment {frag_index}; {err}')
                return -1
            dest.write(decrypt_fragment(fragment, src.read()))
            src.close()
            if not self.params.get('keep_fragments', False):
                self.try_remove(fragment_filename)
        dest.close()
        self.try_remove(f'{tmpfilename}.frag.urls')
        return 0

    def _call_process(self, cmd, info_dict):
        return Popen.run(cmd, text=True, stderr=subprocess.PIPE if self._CAPTURE_STDERR else None)


class CurlFD(ExternalFD):
    AVAILABLE_OPT = '-V'
    _CAPTURE_STDERR = False  # curl writes the progress to stderr

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '--location', '-o', tmpfilename, '--compressed']
        cookie_header = self.ydl.cookiejar.get_cookie_header(info_dict['url'])
        if cookie_header:
            cmd += ['--cookie', cookie_header]
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['--header', f'{key}: {val}']

        cmd += self._bool_option('--continue-at', 'continuedl', '-', '0')
        cmd += self._valueless_option('--silent', 'noprogress')
        cmd += self._valueless_option('--verbose', 'verbose')
        cmd += self._option('--limit-rate', 'ratelimit')
        retry = self._option('--retry', 'retries')
        if len(retry) == 2:
            if retry[1] in ('inf', 'infinite'):
                retry[1] = '2147483647'
            cmd += retry
        cmd += self._option('--max-filesize', 'max_filesize')
        cmd += self._option('--interface', 'source_address')
        cmd += self._option('--proxy', 'proxy')
        cmd += self._valueless_option('--insecure', 'nocheckcertificate')
        cmd += self._configuration_args()
        cmd += ['--', info_dict['url']]
        return cmd


class AxelFD(ExternalFD):
    AVAILABLE_OPT = '-V'

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '-o', tmpfilename]
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['-H', f'{key}: {val}']
        cookie_header = self.ydl.cookiejar.get_cookie_header(info_dict['url'])
        if cookie_header:
            cmd += ['-H', f'Cookie: {cookie_header}', '--max-redirect=0']
        cmd += self._configuration_args()
        cmd += ['--', info_dict['url']]
        return cmd


class WgetFD(ExternalFD):
    AVAILABLE_OPT = '--version'

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '-O', tmpfilename, '-nv', '--compression=auto']
        if self.ydl.cookiejar.get_cookie_header(info_dict['url']):
            cmd += ['--load-cookies', self._write_cookies()]
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['--header', f'{key}: {val}']
        cmd += self._option('--limit-rate', 'ratelimit')
        retry = self._option('--tries', 'retries')
        if len(retry) == 2:
            if retry[1] in ('inf', 'infinite'):
                retry[1] = '0'
            cmd += retry
        cmd += self._option('--bind-address', 'source_address')
        proxy = self.params.get('proxy')
        if proxy:
            for var in ('http_proxy', 'https_proxy'):
                cmd += ['--execute', f'{var}={proxy}']
        cmd += self._valueless_option('--no-check-certificate', 'nocheckcertificate')
        cmd += self._configuration_args()
        cmd += ['--', info_dict['url']]
        return cmd


class Aria2cFD(ExternalFD):
    AVAILABLE_OPT = '-v'
    SUPPORTED_PROTOCOLS = ('http', 'https', 'ftp', 'ftps', 'dash_frag_urls', 'm3u8_frag_urls')

    @staticmethod
    def supports_manifest(manifest):
        UNSUPPORTED_FEATURES = [
            r'#EXT-X-BYTERANGE',  # playlists composed of byte ranges of media files [1]
            # 1. https://tools.ietf.org/html/draft-pantos-http-live-streaming-17#section-4.3.2.2
        ]
        check_results = (not re.search(feature, manifest) for feature in UNSUPPORTED_FEATURES)
        return all(check_results)

    @staticmethod
    def _aria2c_filename(fn):
        return fn if os.path.isabs(fn) else f'.{os.path.sep}{fn}'

    def _call_downloader(self, tmpfilename, info_dict):
        # FIXME: Disabled due to https://github.com/yt-dlp/yt-dlp/issues/5931
        if False and 'no-external-downloader-progress' not in self.params.get('compat_opts', []):
            info_dict['__rpc'] = {
                'port': find_available_port() or 19190,
                'secret': str(uuid.uuid4()),
            }
        return super()._call_downloader(tmpfilename, info_dict)

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '-c', '--no-conf',
               '--console-log-level=warn', '--summary-interval=0', '--download-result=hide',
               '--http-accept-gzip=true', '--file-allocation=none', '-x16', '-j16', '-s16']
        if 'fragments' in info_dict:
            cmd += ['--allow-overwrite=true', '--allow-piece-length-change=true']
        else:
            cmd += ['--min-split-size', '1M']

        if self.ydl.cookiejar.get_cookie_header(info_dict['url']):
            cmd += [f'--load-cookies={self._write_cookies()}']
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['--header', f'{key}: {val}']
        cmd += self._option('--max-overall-download-limit', 'ratelimit')
        cmd += self._option('--interface', 'source_address')
        cmd += self._option('--all-proxy', 'proxy')
        cmd += self._bool_option('--check-certificate', 'nocheckcertificate', 'false', 'true', '=')
        cmd += self._bool_option('--remote-time', 'updatetime', 'true', 'false', '=')
        cmd += self._bool_option('--show-console-readout', 'noprogress', 'false', 'true', '=')
        cmd += self._configuration_args()

        if '__rpc' in info_dict:
            cmd += [
                '--enable-rpc',
                f'--rpc-listen-port={info_dict["__rpc"]["port"]}',
                f'--rpc-secret={info_dict["__rpc"]["secret"]}']

        # aria2c strips out spaces from the beginning/end of filenames and paths.
        # We work around this issue by adding a "./" to the beginning of the
        # filename and relative path, and adding a "/" at the end of the path.
        # See: https://github.com/yt-dlp/yt-dlp/issues/276
        # https://github.com/ytdl-org/youtube-dl/issues/20312
        # https://github.com/aria2/aria2/issues/1373
        dn = os.path.dirname(tmpfilename)
        if dn:
            cmd += ['--dir', self._aria2c_filename(dn) + os.path.sep]
        if 'fragments' not in info_dict:
            cmd += ['--out', self._aria2c_filename(os.path.basename(tmpfilename))]
        cmd += ['--auto-file-renaming=false']

        if 'fragments' in info_dict:
            cmd += ['--uri-selector=inorder']
            url_list_file = f'{tmpfilename}.frag.urls'
            url_list = []
            for frag_index, fragment in enumerate(info_dict['fragments']):
                fragment_filename = f'{os.path.basename(tmpfilename)}-Frag{frag_index}'
                url_list.append('{}\n\tout={}'.format(fragment['url'], self._aria2c_filename(fragment_filename)))
            stream, _ = self.sanitize_open(url_list_file, 'wb')
            stream.write('\n'.join(url_list).encode())
            stream.close()
            cmd += ['-i', self._aria2c_filename(url_list_file)]
        else:
            cmd += ['--', info_dict['url']]
        return cmd

    def aria2c_rpc(self, rpc_port, rpc_secret, method, params=()):
        # Does not actually need to be UUID, just unique
        sanitycheck = str(uuid.uuid4())
        d = json.dumps({
            'jsonrpc': '2.0',
            'id': sanitycheck,
            'method': method,
            'params': [f'token:{rpc_secret}', *params],
        }).encode()
        request = Request(
            f'http://localhost:{rpc_port}/jsonrpc',
            data=d, headers={
                'Content-Type': 'application/json',
                'Content-Length': f'{len(d)}',
            }, proxies={'all': None})
        with self.ydl.urlopen(request) as r:
            resp = json.load(r)
        assert resp.get('id') == sanitycheck, 'Something went wrong with RPC server'
        return resp['result']

    def _call_process(self, cmd, info_dict):
        if '__rpc' not in info_dict:
            return super()._call_process(cmd, info_dict)

        send_rpc = functools.partial(self.aria2c_rpc, info_dict['__rpc']['port'], info_dict['__rpc']['secret'])
        started = time.time()

        fragmented = 'fragments' in info_dict
        frag_count = len(info_dict['fragments']) if fragmented else 1
        status = {
            'filename': info_dict.get('_filename'),
            'status': 'downloading',
            'elapsed': 0,
            'downloaded_bytes': 0,
            'fragment_count': frag_count if fragmented else None,
            'fragment_index': 0 if fragmented else None,
        }
        self._hook_progress(status, info_dict)

        def get_stat(key, *obj, average=False):
            val = tuple(filter(None, map(float, traverse_obj(obj, (..., ..., key))))) or [0]
            return sum(val) / (len(val) if average else 1)

        with Popen(cmd, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as p:
            # Add a small sleep so that RPC client can receive response,
            # or the connection stalls infinitely
            time.sleep(0.2)
            retval = p.poll()
            while retval is None:
                # We don't use tellStatus as we won't know the GID without reading stdout
                # Ref: https://aria2.github.io/manual/en/html/aria2c.html#aria2.tellActive
                active = send_rpc('aria2.tellActive')
                completed = send_rpc('aria2.tellStopped', [0, frag_count])

                downloaded = get_stat('totalLength', completed) + get_stat('completedLength', active)
                speed = get_stat('downloadSpeed', active)
                total = frag_count * get_stat('totalLength', active, completed, average=True)
                if total < downloaded:
                    total = None

                status.update({
                    'downloaded_bytes': int(downloaded),
                    'speed': speed,
                    'total_bytes': None if fragmented else total,
                    'total_bytes_estimate': total,
                    'eta': (total - downloaded) / (speed or 1),
                    'fragment_index': min(frag_count, len(completed) + 1) if fragmented else None,
                    'elapsed': time.time() - started,
                })
                self._hook_progress(status, info_dict)

                if not active and len(completed) >= frag_count:
                    send_rpc('aria2.shutdown')
                    retval = p.wait()
                    break

                time.sleep(0.1)
                retval = p.poll()

            return '', p.stderr.read(), retval


class HttpieFD(ExternalFD):
    AVAILABLE_OPT = '--version'
    EXE_NAME = 'http'

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = ['http', '--download', '--output', tmpfilename, info_dict['url']]

        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += [f'{key}:{val}']

        # httpie 3.1.0+ removes the Cookie header on redirect, so this should be safe for now. [1]
        # If we ever need cookie handling for redirects, we can export the cookiejar into a session. [2]
        # 1: https://github.com/httpie/httpie/security/advisories/GHSA-9w4w-cpc8-h2fq
        # 2: https://httpie.io/docs/cli/sessions
        cookie_header = self.ydl.cookiejar.get_cookie_header(info_dict['url'])
        if cookie_header:
            cmd += [f'Cookie:{cookie_header}']
        return cmd


class FFmpegFD(ExternalFD):
    SUPPORTED_PROTOCOLS = ('http', 'https', 'ftp', 'ftps', 'm3u8', 'm3u8_native', 'rtsp', 'rtmp', 'rtmp_ffmpeg', 'mms', 'http_dash_segments')
    SUPPORTED_FEATURES = (Features.TO_STDOUT, Features.MULTIPLE_FORMATS)

    @classmethod
    def available(cls, path=None):
        return FFmpegPostProcessor().available

    def on_process_started(self, proc, stdin):
        """ Override this in subclasses  """
        pass

    @classmethod
    def can_merge_formats(cls, info_dict, params):
        return (
            info_dict.get('requested_formats')
            and info_dict.get('protocol')
            and not params.get('allow_unplayable_formats')
            and 'no-direct-merge' not in params.get('compat_opts', [])
            and cls.can_download(info_dict))

    def _call_downloader(self, tmpfilename, info_dict):
        ffpp = FFmpegPostProcessor(downloader=self)
        if not ffpp.available:
            self.report_error('m3u8 download detected but ffmpeg could not be found. Please install')
            return False
        ffpp.check_version()

        args = [ffpp.executable, '-y']

        for log_level in ('quiet', 'verbose'):
            if self.params.get(log_level, False):
                args += ['-loglevel', log_level]
                break
        if not self.params.get('verbose'):
            args += ['-hide_banner']

        args += traverse_obj(info_dict, ('downloader_options', 'ffmpeg_args', ...))

        # These exists only for compatibility. Extractors should use
        # info_dict['downloader_options']['ffmpeg_args'] instead
        args += info_dict.get('_ffmpeg_args') or []
        seekable = info_dict.get('_seekable')
        if seekable is not None:
            # setting -seekable prevents ffmpeg from guessing if the server
            # supports seeking(by adding the header `Range: bytes=0-`), which
            # can cause problems in some cases
            # https://github.com/ytdl-org/youtube-dl/issues/11800#issuecomment-275037127
            # http://trac.ffmpeg.org/ticket/6125#comment:10
            args += ['-seekable', '1' if seekable else '0']

        env = None
        proxy = self.params.get('proxy')
        if proxy:
            if not re.match(r'[\da-zA-Z]+://', proxy):
                proxy = f'http://{proxy}'

            if proxy.startswith('socks'):
                self.report_warning(
                    f'{self.get_basename()} does not support SOCKS proxies. Downloading is likely to fail. '
                    'Consider adding --hls-prefer-native to your command.')

            # Since December 2015 ffmpeg supports -http_proxy option (see
            # http://git.videolan.org/?p=ffmpeg.git;a=commit;h=b4eb1f29ebddd60c41a2eb39f5af701e38e0d3fd)
            # We could switch to the following code if we are able to detect version properly
            # args += ['-http_proxy', proxy]
            env = os.environ.copy()
            env['HTTP_PROXY'] = proxy
            env['http_proxy'] = proxy

        protocol = info_dict.get('protocol')

        if protocol == 'rtmp':
            player_url = info_dict.get('player_url')
            page_url = info_dict.get('page_url')
            app = info_dict.get('app')
            play_path = info_dict.get('play_path')
            tc_url = info_dict.get('tc_url')
            flash_version = info_dict.get('flash_version')
            live = info_dict.get('rtmp_live', False)
            conn = info_dict.get('rtmp_conn')
            if player_url is not None:
                args += ['-rtmp_swfverify', player_url]
            if page_url is not None:
                args += ['-rtmp_pageurl', page_url]
            if app is not None:
                args += ['-rtmp_app', app]
            if play_path is not None:
                args += ['-rtmp_playpath', play_path]
            if tc_url is not None:
                args += ['-rtmp_tcurl', tc_url]
            if flash_version is not None:
                args += ['-rtmp_flashver', flash_version]
            if live:
                args += ['-rtmp_live', 'live']
            if isinstance(conn, list):
                for entry in conn:
                    args += ['-rtmp_conn', entry]
            elif isinstance(conn, str):
                args += ['-rtmp_conn', conn]

        start_time, end_time = info_dict.get('section_start') or 0, info_dict.get('section_end')

        selected_formats = info_dict.get('requested_formats') or [info_dict]
        for i, fmt in enumerate(selected_formats):
            is_http = re.match(r'https?://', fmt['url'])
            cookies = self.ydl.cookiejar.get_cookies_for_url(fmt['url']) if is_http else []
            if cookies:
                args.extend(['-cookies', ''.join(
                    f'{cookie.name}={cookie.value}; path={cookie.path}; domain={cookie.domain};\r\n'
                    for cookie in cookies)])
            if fmt.get('http_headers') and is_http:
                # Trailing \r\n after each HTTP header is important to prevent warning from ffmpeg/avconv:
                # [http @ 00000000003d2fa0] No trailing CRLF found in HTTP header.
                args.extend(['-headers', ''.join(f'{key}: {val}\r\n' for key, val in fmt['http_headers'].items())])

            if start_time:
                args += ['-ss', str(start_time)]
            if end_time:
                args += ['-t', str(end_time - start_time)]

            url = fmt['url']
            if self.params.get('enable_file_urls') and url.startswith('file:'):
                # The default protocol_whitelist is 'file,crypto,data' when reading local m3u8 URLs,
                # so only local segments can be read unless we also include 'http,https,tcp,tls'
                args += ['-protocol_whitelist', 'file,crypto,data,http,https,tcp,tls']
                # ffmpeg incorrectly handles 'file:' URLs by only removing the
                # 'file:' prefix and treating the rest as if it's a normal filepath.
                # FFmpegPostProcessor also depends on this behavior, so we need to fixup the URLs:
                # - On Windows/Cygwin, replace 'file:///' and 'file://localhost/' with 'file:'
                # - On *nix, replace 'file://localhost/' with 'file:/'
                # Ref: https://github.com/yt-dlp/yt-dlp/issues/13781
                #      https://trac.ffmpeg.org/ticket/2702
                url = re.sub(r'^file://(?:localhost)?/', 'file:' if os.name == 'nt' else 'file:/', url)

            args += [*self._configuration_args((f'_i{i + 1}', '_i')), '-i', url]

        if not (start_time or end_time) or not self.params.get('force_keyframes_at_cuts'):
            args += ['-c', 'copy']

        if info_dict.get('requested_formats') or protocol == 'http_dash_segments':
            for i, fmt in enumerate(selected_formats):
                stream_number = fmt.get('manifest_stream_number', 0)
                args.extend(['-map', f'{i}:{stream_number}'])

        if self.params.get('test', False):
            args += ['-fs', str(self._TEST_FILE_SIZE)]

        ext = info_dict['ext']
        if protocol in ('m3u8', 'm3u8_native'):
            use_mpegts = (tmpfilename == '-') or self.params.get('hls_use_mpegts')
            if use_mpegts is None:
                use_mpegts = info_dict.get('is_live')
            if use_mpegts:
                args += ['-f', 'mpegts']
            else:
                args += ['-f', 'mp4']
                if (ffpp.basename == 'ffmpeg' and ffpp._features.get('needs_adtstoasc')) and (not info_dict.get('acodec') or info_dict['acodec'].split('.')[0] in ('aac', 'mp4a')):
                    args += ['-bsf:a', 'aac_adtstoasc']
        elif protocol == 'rtmp':
            args += ['-f', 'flv']
        elif ext == 'mp4' and tmpfilename == '-':
            args += ['-f', 'mpegts']
        elif ext == 'unknown_video':
            ext = determine_ext(remove_end(tmpfilename, '.part'))
            if ext == 'unknown_video':
                self.report_warning(
                    'The video format is unknown and cannot be downloaded by ffmpeg. '
                    'Explicitly set the extension in the filename to attempt download in that format')
            else:
                self.report_warning(f'The video format is unknown. Trying to download as {ext} according to the filename')
                args += ['-f', EXT_TO_OUT_FORMATS.get(ext, ext)]
        else:
            args += ['-f', EXT_TO_OUT_FORMATS.get(ext, ext)]

        args += traverse_obj(info_dict, ('downloader_options', 'ffmpeg_args_out', ...))

        args += self._configuration_args(('_o1', '_o', ''))

        args = [encodeArgument(opt) for opt in args]
        args.append(ffpp._ffmpeg_filename_argument(tmpfilename))
        self._debug_cmd(args)

        piped = any(fmt['url'] in ('-', 'pipe:') for fmt in selected_formats)
        with Popen(args, stdin=subprocess.PIPE, env=env) as proc:
            if piped:
                self.on_process_started(proc, proc.stdin)
            try:
                retval = proc.wait()
            except BaseException as e:
                # subprocces.run would send the SIGKILL signal to ffmpeg and the
                # mp4 file couldn't be played, but if we ask ffmpeg to quit it
                # produces a file that is playable (this is mostly useful for live
                # streams). Note that Windows is not affected and produces playable
                # files (see https://github.com/ytdl-org/youtube-dl/issues/8300).
                if isinstance(e, KeyboardInterrupt) and sys.platform != 'win32' and not piped:
                    proc.communicate_or_kill(b'q')
                else:
                    proc.kill(timeout=None)
                raise
            return retval


class AVconvFD(FFmpegFD):
    pass


_BY_NAME = {
    klass.get_basename(): klass
    for name, klass in globals().items()
    if name.endswith('FD') and name not in ('ExternalFD', 'FragmentFD')
}


def list_external_downloaders():
    return sorted(_BY_NAME.keys())


def get_external_downloader(external_downloader):
    """ Given the name of the executable, see whether we support the given downloader """
    bn = os.path.splitext(os.path.basename(external_downloader))[0]
    return _BY_NAME.get(bn) or next((
        klass for klass in _BY_NAME.values() if klass.EXE_NAME in bn
    ), None)
