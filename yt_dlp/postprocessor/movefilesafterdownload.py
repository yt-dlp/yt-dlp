import os

from .common import PostProcessor
from ..compat import shutil
from ..utils import (
    PostProcessingError,
    decodeFilename,
    encodeFilename,
    make_dir,
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
                self.report_warning(f'File "{oldfile}" cannot be found')
                continue
            if os.path.exists(encodeFilename(newfile)):
                if self.get_param('overwrites', True):
                    self.report_warning(f'Replacing existing file "{newfile}"')
                    os.remove(encodeFilename(newfile))
                else:
                    self.report_warning(
                        f'Cannot move file "{oldfile}" out of temporary directory since "{newfile}" already exists. ')
                    continue
            make_dir(newfile, PostProcessingError)
            self.to_screen(f'Moving file "{oldfile}" to "{newfile}"')
            shutil.move(oldfile, newfile)  # os.rename cannot move between volumes

        info['filepath'] = finalpath
        return [], info
