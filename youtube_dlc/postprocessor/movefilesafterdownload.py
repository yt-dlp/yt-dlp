from __future__ import unicode_literals
import os
import shutil

from .common import PostProcessor
from ..utils import (
    encodeFilename,
    make_dir,
    PostProcessingError,
)
from ..compat import compat_str


class MoveFilesAfterDownloadPP(PostProcessor):

    def __init__(self, downloader, files_to_move):
        PostProcessor.__init__(self, downloader)
        self.files_to_move = files_to_move

    @classmethod
    def pp_key(cls):
        return 'MoveFiles'

    def run(self, info):
        if info.get('__dl_filename') is None:
            return [], info
        self.files_to_move.setdefault(info['__dl_filename'], '')
        outdir = os.path.dirname(os.path.abspath(encodeFilename(info['__final_filename'])))

        for oldfile, newfile in self.files_to_move.items():
            if not os.path.exists(encodeFilename(oldfile)):
                self.report_warning('File "%s" cannot be found' % oldfile)
                continue
            if not newfile:
                newfile = compat_str(os.path.join(outdir, os.path.basename(encodeFilename(oldfile))))
            if os.path.abspath(encodeFilename(oldfile)) == os.path.abspath(encodeFilename(newfile)):
                continue
            if os.path.exists(encodeFilename(newfile)):
                if self.get_param('overwrites', True):
                    self.report_warning('Replacing existing file "%s"' % newfile)
                    os.path.remove(encodeFilename(newfile))
                else:
                    self.report_warning(
                        'Cannot move file "%s" out of temporary directory since "%s" already exists. '
                        % (oldfile, newfile))
                    continue
            make_dir(newfile, PostProcessingError)
            self.to_screen('Moving file "%s" to "%s"' % (oldfile, newfile))
            shutil.move(oldfile, newfile)  # os.rename cannot move between volumes

        info['filepath'] = info['__final_filename']
        return [], info
