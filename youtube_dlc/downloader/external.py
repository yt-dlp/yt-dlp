from __future__ import unicode_literals

import os.path
import re
import subprocess
import sys
import time

from .common import FileDownloader
from ..compat import (
    compat_setenv,
    compat_str,
)
from ..postprocessor.ffmpeg import FFmpegPostProcessor, EXT_TO_OUT_FORMATS
from ..utils import (
    cli_option,
    cli_valueless_option,
    cli_bool_option,
    cli_configuration_args,
    encodeFilename,
    encodeArgument,
    handle_youtubedl_headers,
    check_executable,
    is_outdated_version,
)


class ExternalFD(FileDownloader):
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
            self._hook_progress(status)
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
        return self.params.get('external_downloader')

    @classmethod
    def available(cls):
        return check_executable(cls.get_basename(), [cls.AVAILABLE_OPT])

    @classmethod
    def supports(cls, info_dict):
        return info_dict['protocol'] in ('http', 'https', 'ftp', 'ftps')

    @classmethod
    def can_download(cls, info_dict):
        return cls.available() and cls.supports(info_dict)

    def _option(self, command_option, param):
        return cli_option(self.params, command_option, param)

    def _bool_option(self, command_option, param, true_value='true', false_value='false', separator=None):
        return cli_bool_option(self.params, command_option, param, true_value, false_value, separator)

    def _valueless_option(self, command_option, param, expected_value=True):
        return cli_valueless_option(self.params, command_option, param, expected_value)

    def _configuration_args(self, default=[]):
        return cli_configuration_args(self.params, 'external_downloader_args', default)

    def _call_downloader(self, tmpfilename, info_dict):
        """ Either overwrite this or implement _make_cmd """
        cmd = [encodeArgument(a) for a in self._make_cmd(tmpfilename, info_dict)]

        self._debug_cmd(cmd)

        p = subprocess.Popen(
            cmd, stderr=subprocess.PIPE)
        _, stderr = p.communicate()
        if p.returncode != 0:
            self.to_stderr(stderr.decode('utf-8', 'replace'))
        return p.returncode


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
        p = subprocess.Popen(cmd)
        p.communicate()
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

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = [self.exe, '-c']
        cmd += self._configuration_args([
            '--min-split-size', '1M', '--max-connection-per-server', '4'])
        dn = os.path.dirname(tmpfilename)
        if dn:
            cmd += ['--dir', dn]
        cmd += ['--out', os.path.basename(tmpfilename)]
        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['--header', '%s: %s' % (key, val)]
        cmd += self._option('--interface', 'source_address')
        cmd += self._option('--all-proxy', 'proxy')
        cmd += self._bool_option('--check-certificate', 'nocheckcertificate', 'false', 'true', '=')
        cmd += self._bool_option('--remote-time', 'updatetime', 'true', 'false', '=')
        cmd += ['--', info_dict['url']]
        return cmd


class HttpieFD(ExternalFD):
    @classmethod
    def available(cls):
        return check_executable('http', ['--version'])

    def _make_cmd(self, tmpfilename, info_dict):
        cmd = ['http', '--download', '--output', tmpfilename, info_dict['url']]

        if info_dict.get('http_headers') is not None:
            for key, val in info_dict['http_headers'].items():
                cmd += ['%s:%s' % (key, val)]
        return cmd


class FFmpegFD(ExternalFD):
    @classmethod
    def supports(cls, info_dict):
        return info_dict['protocol'] in ('http', 'https', 'ftp', 'ftps', 'm3u8', 'rtsp', 'rtmp', 'mms')

    @classmethod
    def available(cls):
        return FFmpegPostProcessor().available

    def _call_downloader(self, tmpfilename, info_dict):
        url = info_dict['url']
        ffpp = FFmpegPostProcessor(downloader=self)
        if not ffpp.available:
            self.report_error('m3u8 download detected but ffmpeg or avconv could not be found. Please install one.')
            return False
        ffpp.check_version()

        args = [ffpp.executable, '-y']

        for log_level in ('quiet', 'verbose'):
            if self.params.get(log_level, False):
                args += ['-loglevel', log_level]
                break

        seekable = info_dict.get('_seekable')
        if seekable is not None:
            # setting -seekable prevents ffmpeg from guessing if the server
            # supports seeking(by adding the header `Range: bytes=0-`), which
            # can cause problems in some cases
            # https://github.com/ytdl-org/youtube-dl/issues/11800#issuecomment-275037127
            # http://trac.ffmpeg.org/ticket/6125#comment:10
            args += ['-seekable', '1' if seekable else '0']

        args += self._configuration_args()

        # start_time = info_dict.get('start_time') or 0
        # if start_time:
        #     args += ['-ss', compat_str(start_time)]
        # end_time = info_dict.get('end_time')
        # if end_time:
        #     args += ['-t', compat_str(end_time - start_time)]

        if info_dict.get('http_headers') is not None and re.match(r'^https?://', url):
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

        args += ['-i', url, '-c', 'copy']

        if self.params.get('test', False):
            args += ['-fs', compat_str(self._TEST_FILE_SIZE)]

        if protocol in ('m3u8', 'm3u8_native'):
            if self.params.get('hls_use_mpegts', False) or tmpfilename == '-':
                args += ['-f', 'mpegts']
            else:
                args += ['-f', 'mp4']
                if (ffpp.basename == 'ffmpeg' and is_outdated_version(ffpp._versions['ffmpeg'], '3.2', False)) and (not info_dict.get('acodec') or info_dict['acodec'].split('.')[0] in ('aac', 'mp4a')):
                    args += ['-bsf:a', 'aac_adtstoasc']
        elif protocol == 'rtmp':
            args += ['-f', 'flv']
        else:
            args += ['-f', EXT_TO_OUT_FORMATS.get(info_dict['ext'], info_dict['ext'])]

        args = [encodeArgument(opt) for opt in args]
        args.append(encodeFilename(ffpp._ffmpeg_filename_argument(tmpfilename), True))

        self._debug_cmd(args)

        proc = subprocess.Popen(args, stdin=subprocess.PIPE, env=env)
        try:
            retval = proc.wait()
        except KeyboardInterrupt:
            # subprocces.run would send the SIGKILL signal to ffmpeg and the
            # mp4 file couldn't be played, but if we ask ffmpeg to quit it
            # produces a file that is playable (this is mostly useful for live
            # streams). Note that Windows is not affected and produces playable
            # files (see https://github.com/ytdl-org/youtube-dl/issues/8300).
            if sys.platform != 'win32':
                proc.communicate(b'q')
            raise
        return retval


class AVconvFD(FFmpegFD):
    pass


_BY_NAME = dict(
    (klass.get_basename(), klass)
    for name, klass in globals().items()
    if name.endswith('FD') and name != 'ExternalFD'
)


def list_external_downloaders():
    return sorted(_BY_NAME.keys())


def get_external_downloader(external_downloader):
    """ Given the name of the executable, see whether we support the given
        downloader . """
    # Drop .exe extension on Windows
    bn = os.path.splitext(os.path.basename(external_downloader))[0]
    return _BY_NAME[bn]
