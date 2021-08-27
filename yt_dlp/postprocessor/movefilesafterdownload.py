from __future__ import unicode_literals
import os
import shutil

from .common import PostProcessor
from ..utils import (
    decodeFilename,
    encodeFilename,
    make_dir,
    PostProcessingError,
)


class MoveFilesAfterDownloadPP(PostProcessor):

    def __init__(self, downloader=None, downloaded=True):
        PostProcessor.__init__(self, downloader)
        self._downloaded = downloaded

    @classmethod
    def pp_key(cls):
        return 'MoveFiles'

    def run(self, info):
        dl_path, dl_name = os.path.split(encodeFilename(info['filepath']))
        finaldir = info.get('__finaldir', dl_path)
        finalpath = os.path.join(finaldir, dl_name)
        if self._downloaded:
            info['__files_to_move'][info['filepath']] = decodeFilename(finalpath)

        make_newfilename = lambda old: decodeFilename(os.path.join(finaldir, os.path.basename(encodeFilename(old))))
        for oldfile, newfile in info['__files_to_move'].items():
            if not newfile:
                newfile = make_newfilename(oldfile)
            if os.path.abspath(encodeFilename(oldfile)) == os.path.abspath(encodeFilename(newfile)):
                continue
            if not os.path.exists(encodeFilename(oldfile)):
                self.report_warning('File "%s" cannot be found' % oldfile)
                continue
            if os.path.exists(encodeFilename(newfile)):
                if self.get_param('overwrites', True):
                    self.report_warning('Replacing existing file "%s"' % newfile)
                    os.remove(encodeFilename(newfile))
                else:
                    self.report_warning(
                        'Cannot move file "%s" out of temporary directory since "%s" already exists. '
                        % (oldfile, newfile))
                    continue
            make_dir(newfile, PostProcessingError)
            self.to_screen('Moving file "%s" to "%s"' % (oldfile, newfile))
            shutil.move(oldfile, newfile)  # os.rename cannot move between volumes

        info['filepath'] = finalpath
        return [], info
