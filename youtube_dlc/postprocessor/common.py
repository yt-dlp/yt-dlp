from __future__ import unicode_literals

import os

from ..utils import (
    PostProcessingError,
    cli_configuration_args,
    encodeFilename,
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
        if not hasattr(self, 'PP_NAME'):
            self.PP_NAME = self.__class__.__name__[:-2]

    def to_screen(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.to_screen('[%s] %s' % (self.PP_NAME, text), *args, **kwargs)

    def report_warning(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.report_warning(text, *args, **kwargs)

    def report_error(self, text, *args, **kwargs):
        if self._downloader:
            return self._downloader.report_error(text, *args, **kwargs)

    def write_debug(self, text, *args, **kwargs):
        if self.get_param('verbose', False):
            return self._downloader.to_screen('[debug] %s' % text, *args, **kwargs)

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

    def _configuration_args(self, default=[]):
        args = self.get_param('postprocessor_args', {})
        if isinstance(args, list):  # for backward compatibility
            args = {'default': args, 'sponskrub': []}
        return cli_configuration_args(args, self.PP_NAME.lower(), args.get('default', []))


class AudioConversionError(PostProcessingError):
    pass
