import os
from pathlib import Path

from .common import PostProcessor
from ..compat import shutil
from ..utils import (
    PostProcessingError,
    make_dir,
    replace_extension,
)


class MoveFilesAfterDownloadPP(PostProcessor):
    # Map of the keys that contain moveable files and the 'type' of the file
    # for generating the output filename
    CHILD_KEYS = {
        'thumbnails': 'thumbnail',
        'requested_subtitles': 'subtitle',
    }

    def __init__(self, downloader=None, downloaded=True):
        PostProcessor.__init__(self, downloader)
        self._downloaded = downloaded

    @classmethod
    def pp_key(cls):
        return 'MoveFiles'

    def move_file_and_write_to_info(self, info_dict, relevant_dict=None, output_file_type=None):
        relevant_dict = relevant_dict or info_dict
        if 'filepath' not in relevant_dict:
            return

        output_file_type = output_file_type or ''
        current_filepath, final_filepath = self.determine_filepath(info_dict, relevant_dict, output_file_type)
        move_result = self.move_file(info_dict, current_filepath, final_filepath)

        if move_result:
            relevant_dict['filepath'] = move_result
        else:
            del relevant_dict['filepath']

    def determine_filepath(self, info_dict, relevant_dict, output_file_type):
        current_filepath = relevant_dict['filepath']
        prepared_filepath = self._downloader.prepare_filename(info_dict, output_file_type)

        if (output_file_type == 'thumbnail' and info_dict['__multiple_thumbnails']) or output_file_type == 'subtitle':
            desired_extension = ''.join(Path(current_filepath).suffixes[-2:])
        else:
            desired_extension = Path(current_filepath).suffix

        return current_filepath, replace_extension(prepared_filepath, desired_extension[1:])

    def move_file(self, info_dict, current_filepath, final_filepath):
        if not current_filepath or not final_filepath:
            return

        dl_parent_folder = os.path.split(info_dict['filepath'])[0]
        finaldir = info_dict.get('__finaldir', os.path.abspath(dl_parent_folder))

        if not os.path.isabs(current_filepath):
            current_filepath = os.path.join(finaldir, current_filepath)

        if not os.path.isabs(final_filepath):
            final_filepath = os.path.join(finaldir, final_filepath)

        if current_filepath == final_filepath:
            return final_filepath

        if not os.path.exists(current_filepath):
            self.report_warning(f'File "{current_filepath}" cannot be found')
            return

        if os.path.exists(final_filepath):
            if self.get_param('overwrites', True):
                self.report_warning(f'Replacing existing file "{final_filepath}"')
                os.remove(final_filepath)
            else:
                self.report_warning(f'Cannot move file "{current_filepath}" out of temporary directory since "{final_filepath}" already exists. ')
                return

        make_dir(final_filepath, PostProcessingError)
        self.to_screen(f'Moving file "{current_filepath}" to "{final_filepath}"')
        shutil.move(current_filepath, final_filepath)  # os.rename cannot move between volumes

        return final_filepath

    def run(self, info):
        # This represents the main media file (using the 'filepath' key)
        self.move_file_and_write_to_info(info)

        for key, output_file_type in self.CHILD_KEYS.items():
            if key not in info:
                continue

            if isinstance(info[key], (dict, list)):
                iterable = info[key].values() if isinstance(info[key], dict) else info[key]

                for file_dict in iterable:
                    self.move_file_and_write_to_info(info, file_dict, output_file_type)

        return [], info
