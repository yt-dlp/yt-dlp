from __future__ import unicode_literals

import os

from ..compat import compat_str
from ..utils import (
    cli_configuration_args,
    encodeFilename,
    PostProcessingError,
)


class PostProcessor(object):
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
        self._downloader = downloader
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

    def report_error(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.report_error(text, *args, **kwargs)

    def write_debug(self, text, prefix=True, *args, **kwargs):
        tag = '[debug] ' if prefix else ''
        if self.get_param('verbose', False) and self._downloader:
            return self._downloader.to_screen('%s%s' % (tag, text), *args, **kwargs)

    def get_param(self, name, default=None, *args, **kwargs):
        if self._downloader:
            return self._downloader.params.get(name, default, *args, **kwargs)
        return default

    def set_downloader(self, downloader):
        """Sets the downloader for this PP."""
        self._downloader = downloader

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

    def _configuration_args(self, exe, keys=None, default=[], use_compat=True):
        pp_key = self.pp_key().lower()
        exe = exe.lower()
        root_key = exe if pp_key == exe else '%s+%s' % (pp_key, exe)
        keys = ['%s%s' % (root_key, k) for k in (keys or [''])]
        if root_key in keys:
            keys += [root_key] + ([] if pp_key == exe else [(self.pp_key(), exe)]) + ['default']
        else:
            use_compat = False
        return cli_configuration_args(
            self._downloader.params.get('postprocessor_args'),
            keys, default, use_compat)


class AudioConversionError(PostProcessingError):
    pass
