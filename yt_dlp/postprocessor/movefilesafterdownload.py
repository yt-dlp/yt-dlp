import os
from pathlib import Path

from .common import PostProcessor
from ..compat import shutil
from ..utils import (
    PostProcessingError,
    make_dir,
    replace_extension
)
import pdb

class MoveFilesAfterDownloadPP(PostProcessor):
    TOP_LEVEL_KEYS = ['filepath']
    # Map of the keys that contain moveable files and the 'type' of the file
    # for generating the output filename
    CHILD_KEYS = {
        'thumbnails': 'thumbnail',
        'requested_subtitles': 'subtitle'
    }

    def __init__(self, downloader=None, downloaded=True):
        PostProcessor.__init__(self, downloader)
        self._downloaded = downloaded

    @classmethod
    def pp_key(cls):
        return 'MoveFiles'
    
    def move_file_and_write_to_info(self, info_dict, relevant_dict, output_file_type):
        if 'filepath' not in relevant_dict:
            return

        output_file_type = output_file_type or ''
        current_filepath = relevant_dict['filepath']
        # This approach is needed to preserved indexed thumbnail paths from `--write-all-thumbnails`
        # and also to support user-defined extensions (eg: `%(title)s.temp.%(ext)s`)
        extension = ''.join(Path(current_filepath).suffixes)
        name_format = self._downloader.prepare_filename(info_dict, output_file_type)
        final_filepath = replace_extension(name_format, extension)
        move_result = self.move_file(info_dict, current_filepath, final_filepath)
    
        print('*******************')
        print("output_file_type", output_file_type)
        print("name_format", name_format)
        print("current_filepath", current_filepath)
        print("final_filepath", final_filepath)
        print("move_result", move_result)
        print('*******************')

        if move_result:
            relevant_dict['filepath'] = move_result
        else:
            del relevant_dict['filepath']

    def move_file(self, info_dict, current_filepath, final_filepath):
        if not current_filepath or not final_filepath:
            return
        
        dl_path, _dl_name = os.path.split(info_dict['filepath'])
        finaldir = info_dict.get('__finaldir', os.path.abspath(dl_path))

        if not os.path.isabs(current_filepath):
            current_filepath = os.path.join(finaldir, current_filepath)

        if not os.path.isabs(final_filepath):
            final_filepath = os.path.join(finaldir, final_filepath)

        if current_filepath == final_filepath:
            return final_filepath

        if not os.path.exists(current_filepath):
            self.report_warning('File "%s" cannot be found' % current_filepath)
            return

        if os.path.exists(final_filepath):
            if self.get_param('overwrites', True):
                self.report_warning('Replacing existing file "%s"' % final_filepath)
                os.remove(final_filepath)
            else:
                self.report_warning(
                    'Cannot move file "%s" out of temporary directory since "%s" already exists. '
                    % (current_filepath, final_filepath))
                return

        make_dir(final_filepath, PostProcessingError)
        self.to_screen(f'Moving file "{current_filepath}" to "{final_filepath}"')
        shutil.move(current_filepath, final_filepath)  # os.rename cannot move between volumes
        
        return final_filepath

    def run(self, info):
        dl_path, dl_name = os.path.split(info['filepath'])
        finaldir = info.get('__finaldir', os.path.abspath(dl_path))
        # TODO: add one single key to infodict with ALL downloaded files
        # TODO: test with --path temp and stuff
        # TODO: make the below work with not-currently-written filepaths like description, annotations, etc
        #         - Descriptions work, have to do all the other ones too
        #         - I lied, this should become another post-processor
        # TODO: [DONE] probably something with relative paths into absolute again?
        # TODO: remove all __files_to_move stuff when done
        # TODO: add net-new filepaths to `sanitize_info`
        # TODO: consider adding a `infojson_filepath` key in addition to the `infojson_filename` key where the former is the fullpath

        for filepath_key in self.TOP_LEVEL_KEYS:
            self.move_file_and_write_to_info(info, info, None)

        for key, output_file_type in self.CHILD_KEYS.items():
            if key not in info:
                continue

            if isinstance(info[key], list) or isinstance(info[key], dict):
                iterable = info[key].values() if isinstance(info[key], dict) else info[key]

                for file_dict in iterable:
                    self.move_file_and_write_to_info(info, file_dict, output_file_type)

        return [], info

# class MoveFilesAfterDownloadPP(PostProcessor):
#     FILETYPE_KEYS = ['media', 'thumbnails', 'requested_subtitles']

#     def __init__(self, downloader=None, downloaded=True):
#         PostProcessor.__init__(self, downloader)
#         self._downloaded = downloaded

#     @classmethod
#     def pp_key(cls):
#         return 'MoveFiles'

#     def expand_relative_paths(self, files_to_move, finaldir):
#         for filetype in self.FILETYPE_KEYS:
#             if filetype not in files_to_move:
#                 files_to_move[filetype] = []

#             for file_attrs in files_to_move[filetype]:
#                 if not os.path.isabs(file_attrs['final_filepath']):
#                     file_attrs['final_filepath'] = os.path.join(finaldir, file_attrs['final_filepath'])
#                 if not os.path.isabs(file_attrs['current_filepath']):
#                     file_attrs['current_filepath'] = os.path.abspath(file_attrs['current_filepath'])

#         return files_to_move

#     def write_filepath_into_info(self, info, filetype, file_attrs):
#         if filetype == 'media':
#             info['filepath'] = file_attrs['final_filepath']

#         elif filetype == 'thumbnails':
#             for filetype_dict in info[filetype]:
#                 if filetype_dict['id'] == file_attrs['id']:
#                     filetype_dict['filepath'] = file_attrs['final_filepath']

#         elif filetype == 'requested_subtitles':
#             lang = file_attrs['lang']
#             if lang in info[filetype]:
#                 info[filetype][lang]['filepath'] = file_attrs['final_filepath']

#     def run(self, info):
#         dl_path, dl_name = os.path.split(info['filepath'])
#         finaldir = info.get('__finaldir', os.path.abspath(dl_path))

#         th = self._downloader.prepare_filename(info, 'thumbnail')
#         pdb.set_trace()
#         print("th", th)

#         if self._downloaded:
#             info['__files_to_move']['media'] = [{'current_filepath': info['filepath'], 'final_filepath': dl_name}]

#         files_to_move = self.expand_relative_paths(info['__files_to_move'], finaldir)

#         for filetype in self.FILETYPE_KEYS:
#             for file_attrs in files_to_move[filetype]:
#                 current_filepath = file_attrs['current_filepath']
#                 final_filepath = file_attrs['final_filepath']

#                 if not current_filepath or not final_filepath:
#                     continue

#                 if current_filepath == final_filepath:
#                     # This ensures the infojson contains the full filepath even
#                     # when --no-overwrites is used
#                     self.write_filepath_into_info(info, filetype, file_attrs)
#                     continue

#                 if not os.path.exists(current_filepath):
#                     self.report_warning('File "%s" cannot be found' % current_filepath)
#                     continue

#                 if os.path.exists(final_filepath):
#                     if self.get_param('overwrites', True):
#                         self.report_warning('Replacing existing file "%s"' % final_filepath)
#                         os.remove(final_filepath)
#                     else:
#                         self.report_warning(
#                             'Cannot move file "%s" out of temporary directory since "%s" already exists. '
#                             % (current_filepath, final_filepath))
#                         continue

#                 make_dir(final_filepath, PostProcessingError)
#                 self.to_screen(f'Moving file "{current_filepath}" to "{final_filepath}"')
#                 shutil.move(current_filepath, final_filepath)  # os.rename cannot move between volumes
#                 self.write_filepath_into_info(info, filetype, file_attrs)

#         return [], info
