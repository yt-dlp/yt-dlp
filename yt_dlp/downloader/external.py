from __future__ import unicode_literals

import os.path
import re
import subprocess
import sys
import time

from .fragment import FragmentFD
from ..compat import (
    compat_setenv,
    compat_str,
)
from ..postprocessor.ffmpeg import FFmpegPostProcessor, EXT_TO_OUT_FORMATS
from ..utils import (
    cli_option,
    cli_valueless_option,
    cli_bool_option,
    _configuration_args,
    determine_ext,
    encodeFilename,
    encodeArgument,
    handle_youtubedl_headers,
    check_executable,
    Popen,
    remove_end,
)


class ExternalFD(FragmentFD):
    SUPPORTED_PROTOCOLS = ('http', 'https', 'ftp', 'ftps')
    can_download_to_stdout = False

    def real_download(self, filename, info_dict):
        self.report_destination(filename)
        tmpfilename = self.temp_name(filename)

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
            self.to_screen('[%s] Interrupted by user' % self.get_basename())

        if retval == 0:
            status = {
                'filename': filename,
                'status': 'finished',
                'elapsed': time.time() - started,
            }
            if filename != '-':
                fsize = os.path.getsize(encodeFilename(tmpfilename))
                self.to_screen('\r[%s] Downloaded %s bytes' % (self.get_basename(), fsize))
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

    @property
    def exe(self):
        return self.get_basename()

    @classmethod
    def available(cls, path=None):
        path = check_executable(path or cls.get_basename(), [cls.AVAILABLE_OPT])
        if path:
            cls.exe = path
            return path
        return False

    @classmethod
    def supports(cls, info_dict):
        return (
            (cls.can_download_to_stdout or not info_dict.get('to_stdout'))
            and info_dict['protocol'] in cls.SUPPORTED_PROTOCOLS)

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
            self.get_basename(), self.params.get('external_downloader_args'), self.get_basename(),
            keys, *args, **kwargs)

    def _call_downloader(self, tmpfilename, info_dict):
        """ Either overwrite this or implement _make_cmd """
        cmd = [encodeArgument(a) for a in self._make_cmd(tmpfilename, info_dict)]

        self._debug_cmd(cmd)

        if 'fragments' not in info_dict:
            p = Popen(cmd, stderr=subprocess.PIPE)
            _, stderr = p.communicate_or_kill()
            if p.returncode != 0:
                self.to_stderr(stderr.decode('utf-8', 'replace'))
            return p.returncode

        fragment_retries = self.params.get('fragment_retries', 0)
        skip_unavailable_fragments = self.params.get('skip_unavailable_fragments', True)

        count = 0
        while count <= fragment_retries:
            p = Popen(cmd, stderr=subprocess.PIPE)
            _, stderr = p.communicate_or_kill()
            if p.returncode == 0:
                break
            # TODO: Decide whether to retry based on error code
            # https://aria2.github.io/manual/en/html/aria2c.html#exit-status
            self.to_stderr(stderr.decode('utf-8', 'replace'))
            count += 1
            if count <= fragment_retries:
                self.to_screen(
                    '[%s] Got error. Retrying fragments (attempt %d of %s)...'
                    % (self.get_basename(), count, self.format_retries(fragment_retries)))
        if count > fragment_retries:
            if not skip_unavailable_fragments:
                self.report_error('Giving up after %s fragment retries' % fragment_retries)
                return -1

        decrypt_fragment = self.decrypter(info_dict)
        dest, _ = self.sanitize_open(tmpfilename, 'wb')
        for frag_index, fragment in enumerate(info_dict['fragments']):
            fragment_filename = '%s-Frag%d' % (tmpfilename, frag_index)
            try:
                src, _ = self.sanitize_open(fragment_filename, 'rb')
            except IOError as err:
                if skip_unavailable_fragments and frag_index > 1:
                    self.report_skip_fragment(frag_index, err)
                    continue
                self.report_error(f'Unable to open fragment {frag_index}; {err}')
                return -1
            dest.write(decrypt_fragment(fragment, src.read()))
            src.close()
            if not self.params.get('keep_fragments', False):
                os.remove(encodeFilename(fragment_filename))
        dest.close()
        os.remove(encodeFilename('%s.frag.urls' % tmpfilename))
        return 0


class CurlFD(ExternalFD):
    AVAILABLE_OPT = '-V'

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '--location', '-o', tmpfilename]
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['--header', '%s: %s' % (key, val)]

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

    def _call_downloader(self, tmpfilename, info_dict):
        cmd = [encodeArgument(a) for a in self._make_cmd(tmpfilename, info_dict)]

        self._debug_cmd(cmd)

        # curl writes the progress to stderr so don't capture it.
        p = Popen(cmd)
        p.communicate_or_kill()
        return p.returncode


class AxelFD(ExternalFD):
    AVAILABLE_OPT = '-V'

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '-o', tmpfilename]
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['-H', '%s: %s' % (key, val)]
        cmd += self._configuration_args()
        cmd += ['--', info_dict['url']]
        return cmd


class WgetFD(ExternalFD):
    AVAILABLE_OPT = '--version'

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '-O', tmpfilename, '-nv', '--no-cookies']
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['--header', '%s: %s' % (key, val)]
        cmd += self._option('--limit-rate', 'ratelimit')
        retry = self._option('--tries', 'retries')
        if len(retry) == 2:
            if retry[1] in ('inf', 'infinite'):
                retry[1] = '0'
            cmd += retry
        cmd += self._option('--bind-address', 'source_address')
        cmd += self._option('--proxy', 'proxy')
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

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '-c',
               '--console-log-level=warn', '--summary-interval=0', '--download-result=hide',
               '--file-allocation=none', '-x16', '-j16', '-s16']
        if 'fragments' in info_dict:
            cmd += ['--allow-overwrite=true', '--allow-piece-length-change=true']
        else:
            cmd += ['--min-split-size', '1M']

        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['--header', '%s: %s' % (key, val)]
        cmd += self._option('--max-overall-download-limit', 'ratelimit')
        cmd += self._option('--interface', 'source_address')
        cmd += self._option('--all-proxy', 'proxy')
        cmd += self._bool_option('--check-certificate', 'nocheckcertificate', 'false', 'true', '=')
        cmd += self._bool_option('--remote-time', 'updatetime', 'true', 'false', '=')
        cmd += self._bool_option('--show-console-readout', 'noprogress', 'false', 'true', '=')
        cmd += self._configuration_args()

        # aria2c strips out spaces from the beginning/end of filenames and paths.
        # We work around this issue by adding a "./" to the beginning of the
        # filename and relative path, and adding a "/" at the end of the path.
        # See: https://github.com/yt-dlp/yt-dlp/issues/276
        # https://github.com/ytdl-org/youtube-dl/issues/20312
        # https://github.com/aria2/aria2/issues/1373
        dn = os.path.dirname(tmpfilename)
        if dn:
            if not os.path.isabs(dn):
                dn = '.%s%s' % (os.path.sep, dn)
            cmd += ['--dir', dn + os.path.sep]
        if 'fragments' not in info_dict:
            cmd += ['--out', '.%s%s' % (os.path.sep, os.path.basename(tmpfilename))]
        cmd += ['--auto-file-renaming=false']

        if 'fragments' in info_dict:
            cmd += ['--file-allocation=none', '--uri-selector=inorder']
            url_list_file = '%s.frag.urls' % tmpfilename
            url_list = []
            for frag_index, fragment in enumerate(info_dict['fragments']):
                fragment_filename = '%s-Frag%d' % (os.path.basename(tmpfilename), frag_index)
                url_list.append('%s\n\tout=%s' % (fragment['url'], fragment_filename))
            stream, _ = self.sanitize_open(url_list_file, 'wb')
            stream.write('\n'.join(url_list).encode('utf-8'))
            stream.close()
            cmd += ['-i', url_list_file]
        else:
            cmd += ['--', info_dict['url']]
        return cmd


class HttpieFD(ExternalFD):
    AVAILABLE_OPT = '--version'

    @classmethod
    def available(cls, path=None):
        return super().available(path or 'http')

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = ['http', '--download', '--output', tmpfilename, info_dict['url']]

        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['%s:%s' % (key, val)]
        return cmd


class FFmpegFD(ExternalFD):
    SUPPORTED_PROTOCOLS = ('http', 'https', 'ftp', 'ftps', 'm3u8', 'm3u8_native', 'rtsp', 'rtmp', 'rtmp_ffmpeg', 'mms', 'http_dash_segments')
    can_download_to_stdout = True

    @classmethod
    def available(cls, path=None):
        # TODO: Fix path for ffmpeg
        # Fixme: This may be wrong when --ffmpeg-location is used
        return FFmpegPostProcessor().available

    @classmethod
    def supports(cls, info_dict):
        return all(proto in cls.SUPPORTED_PROTOCOLS for proto in info_dict['protocol'].split('+'))

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
        urls = [f['url'] for f in info_dict.get('requested_formats', [])] or [info_dict['url']]
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

        args += info_dict.get('_ffmpeg_args', [])

        # This option exists only for compatibility. Extractors should use `_ffmpeg_args` instead
        seekable = info_dict.get('_seekable')
        if seekable is not None:
            # setting -seekable prevents ffmpeg from guessing if the server
            # supports seeking(by adding the header `Range: bytes=0-`), which
            # can cause problems in some cases
            # https://github.com/ytdl-org/youtube-dl/issues/11800#issuecomment-275037127
            # http://trac.ffmpeg.org/ticket/6125#comment:10
            args += ['-seekable', '1' if seekable else '0']

        # start_time = info_dict.get('start_time') or 0
        # if start_time:
        #     args += ['-ss', compat_str(start_time)]
        # end_time = info_dict.get('end_time')
        # if end_time:
        #     args += ['-t', compat_str(end_time - start_time)]

        if info_dict.get('http_headers') is not None and re.match(r'^https?://', urls[0]):
            # Trailing \r\n after each HTTP header is important to prevent warning from ffmpeg/avconv:
            # [http @ 00000000003d2fa0] No trailing CRLF found in HTTP header.
            headers = handle_youtubedl_headers(info_dict['http_headers'])
            args += [
                '-headers',
                ''.join('%s: %s\r\n' % (key, val) for key, val in headers.items())]

        env = None
        proxy = self.params.get('proxy')
        if proxy:
            if not re.match(r'^[\da-zA-Z]+://', proxy):
                proxy = 'http://%s' % proxy

            if proxy.startswith('socks'):
                self.report_warning(
                    '%s does not support SOCKS proxies. Downloading is likely to fail. '
                    'Consider adding --hls-prefer-native to your command.' % self.get_basename())

            # Since December 2015 ffmpeg supports -http_proxy option (see
            # http://git.videolan.org/?p=ffmpeg.git;a=commit;h=b4eb1f29ebddd60c41a2eb39f5af701e38e0d3fd)
            # We could switch to the following code if we are able to detect version properly
            # args += ['-http_proxy', proxy]
            env = os.environ.copy()
            compat_setenv('HTTP_PROXY', proxy, env=env)
            compat_setenv('http_proxy', proxy, env=env)

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
            elif isinstance(conn, compat_str):
                args += ['-rtmp_conn', conn]

        for i, url in enumerate(urls):
            args += self._configuration_args((f'_i{i + 1}', '_i')) + ['-i', url]

        args += ['-c', 'copy']
        if info_dict.get('requested_formats') or protocol == 'http_dash_segments':
            for (i, fmt) in enumerate(info_dict.get('requested_formats') or [info_dict]):
                stream_number = fmt.get('manifest_stream_number', 0)
                args.extend(['-map', f'{i}:{stream_number}'])

        if self.params.get('test', False):
            args += ['-fs', compat_str(self._TEST_FILE_SIZE)]

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

        args += self._configuration_args(('_o1', '_o', ''))

        args = [encodeArgument(opt) for opt in args]
        args.append(encodeFilename(ffpp._ffmpeg_filename_argument(tmpfilename), True))
        self._debug_cmd(args)

        proc = Popen(args, stdin=subprocess.PIPE, env=env)
        if url in ('-', 'pipe:'):
            self.on_process_started(proc, proc.stdin)
        try:
            retval = proc.wait()
        except BaseException as e:
            # subprocces.run would send the SIGKILL signal to ffmpeg and the
            # mp4 file couldn't be played, but if we ask ffmpeg to quit it
            # produces a file that is playable (this is mostly useful for live
            # streams). Note that Windows is not affected and produces playable
            # files (see https://github.com/ytdl-org/youtube-dl/issues/8300).
            if isinstance(e, KeyboardInterrupt) and sys.platform != 'win32' and url not in ('-', 'pipe:'):
                proc.communicate_or_kill(b'q')
            else:
                proc.kill()
                proc.wait()
            raise
        return retval


class AVconvFD(FFmpegFD):
    pass


_BY_NAME = dict(
    (klass.get_basename(), klass)
    for name, klass in globals().items()
    if name.endswith('FD') and name not in ('ExternalFD', 'FragmentFD')
)


def list_external_downloaders():
    return sorted(_BY_NAME.keys())


def get_external_downloader(external_downloader):
    """ Given the name of the executable, see whether we support the given
        downloader . """
    # Drop .exe extension on Windows
    bn = os.path.splitext(os.path.basename(external_downloader))[0]
    return _BY_NAME.get(bn)
