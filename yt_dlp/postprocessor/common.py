import functools
import json
import os

from ..networking import Request
from ..networking.exceptions import HTTPError, network_exceptions
from ..utils import (
    PostProcessingError,
    RetryManager,
    _configuration_args,
    deprecation_warning,
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
        self.PP_NAME = self.pp_key()

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
            os.utime(path, (atime, mtime))
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

    def report_progress(self, s):
        s['_default_template'] = '%(postprocessor)s %(status)s' % s  # noqa: UP031
        if not self._downloader:
            return

        progress_dict = s.copy()
        progress_dict.pop('info_dict')
        progress_dict = {'info': s['info_dict'], 'progress': progress_dict}

        progress_template = self.get_param('progress_template', {})
        tmpl = progress_template.get('postprocess')
        if tmpl:
            self._downloader.to_screen(
                self._downloader.evaluate_outtmpl(tmpl, progress_dict), quiet=False)

        self._downloader.to_console_title(self._downloader.evaluate_outtmpl(
            progress_template.get('postprocess-title') or 'yt-dlp %(progress._default_template)s',
            progress_dict))

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
