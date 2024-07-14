import functools
import json
import os
import sys

from ..minicurses import (
    BreaklineStatusPrinter,
    MultilineLogger,
    MultilinePrinter,
    QuietMultilinePrinter,
)
from ..networking import Request
from ..networking.exceptions import HTTPError, network_exceptions
from ..utils import (
    FormatProgressInfos,
    Namespace,
    PostProcessingError,
    RetryManager,
    _configuration_args,
    deprecation_warning,
    encodeFilename,
    format_bytes,
    join_nonempty,
    try_call,
)


class PostProcessorMetaClass(type):
    @staticmethod
    def run_wrapper(func):
        @functools.wraps(func)
        def run(self, info, *args, **kwargs):
            info_copy = self._copy_infodict(info)
            self._hook_progress({'status': 'started'}, info_copy)
            ret = func(self, info, *args, **kwargs)
            if ret is not None:
                _, info = ret
            self._hook_progress({'status': 'finished'}, info_copy)
            return ret
        return run

    def __new__(cls, name, bases, attrs):
        if 'run' in attrs:
            attrs['run'] = cls.run_wrapper(attrs['run'])
        return type.__new__(cls, name, bases, attrs)


class PostProcessor(metaclass=PostProcessorMetaClass):
    """Post Processor class.

    PostProcessor objects can be added to downloaders with their
    add_post_processor() method. When the downloader has finished a
    successful download, it will take its internal chain of PostProcessors
    and start calling the run() method on each one of them, first with
    an initial argument and then with the returned value of the previous
    PostProcessor.

    PostProcessor objects follow a "mutual registration" process similar
    to InfoExtractor objects.

    Optionally PostProcessor can use a list of additional command-line arguments
    with self._configuration_args.
    """

    _downloader = None

    def __init__(self, downloader=None):
        self._progress_hooks = []
        self.add_progress_hook(self.report_progress)
        self.set_downloader(downloader)
        self._out_files = self.set_out_files()
        self.PP_NAME = self.pp_key()
        self._prepare_multiline_status()

    @classmethod
    def pp_key(cls):
        name = cls.__name__[:-2]
        return name[6:] if name[:6].lower() == 'ffmpeg' else name

    def to_screen(self, text, prefix=True, *args, **kwargs):
        if self._downloader:
            tag = f'[{self.PP_NAME}] ' if prefix else ''
            return self._downloader.to_screen(f'{tag}{text}', *args, **kwargs)

    def report_warning(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.report_warning(text, *args, **kwargs)

    def deprecation_warning(self, msg):
        warn = getattr(self._downloader, 'deprecation_warning', deprecation_warning)
        return warn(msg, stacklevel=1)

    def deprecated_feature(self, msg):
        if self._downloader:
            return self._downloader.deprecated_feature(msg)
        return deprecation_warning(msg, stacklevel=1)

    def report_error(self, text, *args, **kwargs):
        self.deprecation_warning('"yt_dlp.postprocessor.PostProcessor.report_error" is deprecated. '
                                 'raise "yt_dlp.utils.PostProcessingError" instead')
        if self._downloader:
            return self._downloader.report_error(text, *args, **kwargs)

    def write_debug(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.write_debug(text, *args, **kwargs)

    def _delete_downloaded_files(self, *files_to_delete, **kwargs):
        if self._downloader:
            return self._downloader._delete_downloaded_files(*files_to_delete, **kwargs)
        for filename in set(filter(None, files_to_delete)):
            os.remove(filename)

    def get_param(self, name, default=None, *args, **kwargs):
        if self._downloader:
            return self._downloader.params.get(name, default, *args, **kwargs)
        return default

    def set_out_files(self):
        if not self._downloader:
            return None
        return getattr(self._downloader, '_out_files', None) or self._downloader.ydl._out_files

    def set_downloader(self, downloader):
        """Sets the downloader for this PP."""
        self._downloader = downloader
        for ph in getattr(downloader, '_postprocessor_hooks', []):
            self.add_progress_hook(ph)

    def _copy_infodict(self, info_dict):
        return getattr(self._downloader, '_copy_infodict', dict)(info_dict)

    @staticmethod
    def _restrict_to(*, video=True, audio=True, images=True, simulated=True):
        allowed = {'video': video, 'audio': audio, 'images': images}

        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, info):
                if not simulated and (self.get_param('simulate') or self.get_param('skip_download')):
                    return [], info
                format_type = (
                    'video' if info.get('vcodec') != 'none'
                    else 'audio' if info.get('acodec') != 'none'
                    else 'images')
                if allowed[format_type]:
                    return func(self, info)
                else:
                    self.to_screen(f'Skipping {format_type}')
                    return [], info
            return wrapper
        return decorator

    def run(self, information):
        """Run the PostProcessor.

        The "information" argument is a dictionary like the ones
        composed by InfoExtractors. The only difference is that this
        one has an extra field called "filepath" that points to the
        downloaded file.

        This method returns a tuple, the first element is a list of the files
        that can be deleted, and the second of which is the updated
        information.

        In addition, this method may raise a PostProcessingError
        exception if post processing fails.
        """
        return [], information  # by default, keep file and do nothing

    def try_utime(self, path, atime, mtime, errnote='Cannot update utime of file'):
        try:
            os.utime(encodeFilename(path), (atime, mtime))
        except Exception:
            self.report_warning(errnote)

    def _configuration_args(self, exe, *args, **kwargs):
        return _configuration_args(
            self.pp_key(), self.get_param('postprocessor_args'), exe, *args, **kwargs)

    def _hook_progress(self, status, info_dict):
        if not self._progress_hooks:
            return
        status.update({
            'info_dict': info_dict,
            'postprocessor': self.pp_key(),
        })
        for ph in self._progress_hooks:
            ph(status)

    def add_progress_hook(self, ph):
        # See YoutubeDl.py (search for postprocessor_hooks) for a description of this interface
        self._progress_hooks.append(ph)

    def report_destination(self, filename):
        """Report destination filename."""
        self.to_screen('[processing] Destination: ' + filename)

    def _prepare_multiline_status(self, lines=1):
        if self._downloader:
            if self._downloader.params.get('noprogress'):
                self._multiline = QuietMultilinePrinter()
            elif self._downloader.params.get('logger'):
                self._multiline = MultilineLogger(self._downloader.params['logger'], lines)
            elif self._downloader.params.get('progress_with_newline'):
                self._multiline = BreaklineStatusPrinter(self._downloader._out_files.out, lines)
            elif hasattr(self._downloader, "_out_files"):
                self._multiline = MultilinePrinter(self._downloader._out_files.out, lines, not self._downloader.params.get('quiet'))
            else:
                self._multiline = MultilinePrinter(sys.stdout, lines, not self._downloader.params.get('quiet'))
            self._multiline.allow_colors = self._multiline._HAVE_FULLCAP and not self._downloader.params.get('no_color')
        else:
            self._multiline = MultilinePrinter(sys.stdout, lines, True)
            self._multiline.allow_colors = self._multiline._HAVE_FULLCAP

    def _finish_multiline_status(self):
        self._multiline.end()

    ProgressStyles = Namespace(
        processed_bytes='light blue',
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

        progress_template = self._downloader.params.get('progress_template', {})
        self._multiline.print_at_line(self._downloader.evaluate_outtmpl(
            progress_template.get('process') or '[processing] %(progress._default_template)s',
            progress_dict), s.get('progress_idx') or 0)
        self._downloader.to_console_title(self._downloader.evaluate_outtmpl(
            progress_template.get('download-title') or 'yt-dlp %(progress._default_template)s',
            progress_dict))

    def _format_progress(self, *args, **kwargs):
        return self._downloader._format_text(
            self._multiline.stream, self._multiline.allow_colors, *args, **kwargs)

    def report_progress(self, s):
        def with_fields(*tups, default=''):
            for *fields, tmpl in tups:
                if all(s.get(f) is not None for f in fields):
                    return tmpl
            return default

        if not self._downloader:
            return

        if s['status'] == 'finished':
            if self._downloader.params.get('noprogress'):
                self.to_screen('[processing] Download completed')
            speed = try_call(lambda: s['total_bytes'] / s['elapsed'])
            s.update({
                'speed': speed,
                '_speed_str': FormatProgressInfos.format_speed(speed).strip(),
                '_total_bytes_str': format_bytes(s.get('total_bytes')),
                '_elapsed_str': FormatProgressInfos.format_seconds(s.get('elapsed')),
                '_percent_str': FormatProgressInfos.format_percent(100),
            })
            self._report_progress_status(s, join_nonempty(
                '100%%',
                with_fields(('total_bytes', 'of %(_total_bytes_str)s')),
                with_fields(('elapsed', 'in %(_elapsed_str)s')),
                with_fields(('speed', 'at %(_speed_str)s')),
                delim=' '))

        if s['status'] != 'processing':
            return

        s.update({
            '_eta_str': FormatProgressInfos.format_eta(s.get('eta')),
            '_speed_str': FormatProgressInfos.format_speed(s.get('speed')),
            '_percent_str': FormatProgressInfos.format_percent(try_call(
                lambda: 100 * s['processed_bytes'] / s['total_bytes'],
                lambda: 100 * s['processed_bytes'] / s['total_bytes_estimate'],
                lambda: s['processed_bytes'] == 0 and 0)),
            '_total_bytes_str': format_bytes(s.get('total_bytes')),
            '_total_bytes_estimate_str': format_bytes(s.get('total_bytes_estimate')),
            '_processed_bytes_str': format_bytes(s.get('processed_bytes')),
            '_elapsed_str': FormatProgressInfos.format_seconds(s.get('elapsed')),
        })

        msg_template = with_fields(
            ('total_bytes', '%(_percent_str)s of %(_total_bytes_str)s at %(_speed_str)s ETA %(_eta_str)s'),
            ('processed_bytes', 'elapsed', '%(_processed_bytes_str)s at %(_speed_str)s (%(_elapsed_str)s)'),
            ('processed_bytes', '%(_processed_bytes_str)s at %(_speed_str)s'),
            default='%(_percent_str)s at %(_speed_str)s ETA %(_eta_str)s')

        self._report_progress_status(s, msg_template)

    def _retry_download(self, err, count, retries):
        # While this is not an extractor, it behaves similar to one and
        # so obey extractor_retries and "--retry-sleep extractor"
        RetryManager.report_retry(err, count, retries, info=self.to_screen, warn=self.report_warning,
                                  sleep_func=self.get_param('retry_sleep_functions', {}).get('extractor'))

    def _download_json(self, url, *, expected_http_errors=(404,)):
        self.write_debug(f'{self.PP_NAME} query: {url}')
        for retry in RetryManager(self.get_param('extractor_retries', 3), self._retry_download):
            try:
                rsp = self._downloader.urlopen(Request(url))
            except network_exceptions as e:
                if isinstance(e, HTTPError) and e.status in expected_http_errors:
                    return None
                retry.error = PostProcessingError(f'Unable to communicate with {self.PP_NAME} API: {e}')
                continue
        return json.loads(rsp.read().decode(rsp.headers.get_param('charset') or 'utf-8'))


class AudioConversionError(PostProcessingError):  # Deprecated
    pass
