import os

from .common import PostProcessor
from ..compat import shutil
from ..utils import (
    PostProcessingError,
    make_dir,
)


class MoveFilesAfterDownloadPP(PostProcessor):
    FILETYPE_KEYS = ['media', 'thumbnails', 'requested_subtitles']

    def __init__(self, downloader=None, downloaded=True):
        PostProcessor.__init__(self, downloader)
        self._downloaded = downloaded

    @classmethod
    def pp_key(cls):
        return 'MoveFiles'

    def expand_relative_paths(self, files_to_move, finaldir):
        for filetype in self.FILETYPE_KEYS:
            if filetype not in files_to_move:
                files_to_move[filetype] = []

            for file_attrs in files_to_move[filetype]:
                if not os.path.isabs(file_attrs['final_filepath']):
                    file_attrs['final_filepath'] = os.path.join(finaldir, file_attrs['final_filepath'])
                if not os.path.isabs(file_attrs['current_filepath']):
                    file_attrs['current_filepath'] = os.path.abspath(file_attrs['current_filepath'])

        return files_to_move

    def write_filepath_into_info(self, info, filetype, file_attrs):
        if filetype == 'media':
            info['filepath'] = file_attrs['final_filepath']

        elif filetype == 'thumbnails':
            for filetype_dict in info[filetype]:
                if filetype_dict['id'] == file_attrs['id']:
                    filetype_dict['filepath'] = file_attrs['final_filepath']

        elif filetype == 'requested_subtitles':
            lang = file_attrs['lang']
            if lang in info[filetype]:
                info[filetype][lang]['filepath'] = file_attrs['final_filepath']

    def run(self, info):
        dl_path, dl_name = os.path.split(info['filepath'])
        finaldir = info.get('__finaldir', os.path.abspath(dl_path))

        if self._downloaded:
            info['__files_to_move']['media'] = [{'current_filepath': info['filepath'], 'final_filepath': dl_name}]

        files_to_move = self.expand_relative_paths(info['__files_to_move'], finaldir)

        for filetype in self.FILETYPE_KEYS:
            for file_attrs in files_to_move[filetype]:
                current_filepath = file_attrs['current_filepath']
                final_filepath = file_attrs['final_filepath']

                if not current_filepath or not final_filepath:
                    continue

                if current_filepath == final_filepath:
                    # This ensures the infojson contains the full filepath even
                    # when --no-overwrites is used
                    self.write_filepath_into_info(info, filetype, file_attrs)
                    continue

                if not os.path.exists(current_filepath):
                    self.report_warning('File "%s" cannot be found' % current_filepath)
                    continue

                if os.path.exists(final_filepath):
                    if self.get_param('overwrites', True):
                        self.report_warning('Replacing existing file "%s"' % final_filepath)
                        os.remove(final_filepath)
                    else:
                        self.report_warning(
                            'Cannot move file "%s" out of temporary directory since "%s" already exists. '
                            % (current_filepath, final_filepath))
                        continue

                make_dir(final_filepath, PostProcessingError)
                self.to_screen(f'Moving file "{current_filepath}" to "{final_filepath}"')
                shutil.move(current_filepath, final_filepath)  # os.rename cannot move between volumes
                self.write_filepath_into_info(info, filetype, file_attrs)

        return [], info
