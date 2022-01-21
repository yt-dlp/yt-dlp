from __future__ import unicode_literals

import functools
import os

from ..compat import compat_str
from ..utils import (
    _configuration_args,
    encodeFilename,
    PostProcessingError,
    write_string,
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

    The chain will be stopped if one of them ever returns None or the end
    of the chain is reached.

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
        return compat_str(name[6:]) if name[:6].lower() == 'ffmpeg' else name

    def to_screen(self, text, prefix=True, *args, **kwargs):
        tag = '[%s] ' % self.PP_NAME if prefix else ''
        if self._downloader:
            return self._downloader.to_screen('%s%s' % (tag, text), *args, **kwargs)

    def report_warning(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.report_warning(text, *args, **kwargs)

    def deprecation_warning(self, text):
        if self._downloader:
            return self._downloader.deprecation_warning(text)
        write_string(f'DeprecationWarning: {text}')

    def report_error(self, text, *args, **kwargs):
        # Exists only for compatibility. Do not use
        if self._downloader:
            return self._downloader.report_error(text, *args, **kwargs)

    def write_debug(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.write_debug(text, *args, **kwargs)

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
    def _restrict_to(*, video=True, audio=True, images=True):
        allowed = {'video': video, 'audio': audio, 'images': images}

        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, info):
                format_type = (
                    'video' if info.get('vcodec') != 'none'
                    else 'audio' if info.get('acodec') != 'none'
                    else 'images')
                if allowed[format_type]:
                    return func(self, info)
                else:
                    self.to_screen('Skipping %s' % format_type)
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

    def report_progress(self, s):
        s['_default_template'] = '%(postprocessor)s %(status)s' % s

        progress_dict = s.copy()
        progress_dict.pop('info_dict')
        progress_dict = {'info': s['info_dict'], 'progress': progress_dict}

        progress_template = self.get_param('progress_template', {})
        tmpl = progress_template.get('postprocess')
        if tmpl:
            self._downloader.to_stdout(self._downloader.evaluate_outtmpl(tmpl, progress_dict))

        self._downloader.to_console_title(self._downloader.evaluate_outtmpl(
            progress_template.get('postprocess-title') or 'yt-dlp %(progress._default_template)s',
            progress_dict))


class AudioConversionError(PostProcessingError):
    pass
