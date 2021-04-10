# coding: utf-8
from __future__ import unicode_literals

import os
import subprocess
import struct
import re
import base64

try:
    import mutagen
    has_mutagen = True
except ImportError:
    has_mutagen = False

from .ffmpeg import (
    FFmpegPostProcessor,
    FFmpegThumbnailsConvertorPP,
)
from ..utils import (
    check_executable,
    encodeArgument,
    encodeFilename,
    error_to_compat_str,
    PostProcessingError,
    prepend_extension,
    process_communicate_or_kill,
    shell_quote,
)


class EmbedThumbnailPPError(PostProcessingError):
    pass


class EmbedThumbnailPP(FFmpegPostProcessor):

    def __init__(self, downloader=None, already_have_thumbnail=False):
        FFmpegPostProcessor.__init__(self, downloader)
        self._already_have_thumbnail = already_have_thumbnail

    def run(self, info):
        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        if not info.get('thumbnails'):
            self.to_screen('There aren\'t any thumbnails to embed')
            return [], info

        thumbnail_filename = info['thumbnails'][-1]['filepath']
        if not os.path.exists(encodeFilename(thumbnail_filename)):
            self.report_warning('Skipping embedding the thumbnail because the file is missing.')
            return [], info

        # Correct extension for WebP file with wrong extension (see #25687, #25717)
        convertor = FFmpegThumbnailsConvertorPP(self._downloader)
        convertor.fixup_webp(info, -1)

        original_thumbnail = thumbnail_filename = info['thumbnails'][-1]['filepath']

        # Convert unsupported thumbnail formats to JPEG (see #25687, #25717)
        _, thumbnail_ext = os.path.splitext(thumbnail_filename)
        if thumbnail_ext not in ('jpg', 'png'):
            thumbnail_filename = convertor.convert_thumbnail(thumbnail_filename, 'jpg')
            thumbnail_ext = 'jpg'

        mtime = os.stat(encodeFilename(filename)).st_mtime

        success = True
        if info['ext'] == 'mp3':
            options = [
                '-c', 'copy', '-map', '0:0', '-map', '1:0', '-id3v2_version', '3',
                '-metadata:s:v', 'title="Album cover"', '-metadata:s:v', 'comment="Cover (front)"']

            self.to_screen('Adding thumbnail to "%s"' % filename)
            self.run_ffmpeg_multiple_files([filename, thumbnail_filename], temp_filename, options)

        elif info['ext'] in ['mkv', 'mka']:
            options = ['-c', 'copy', '-map', '0', '-dn']

            mimetype = 'image/%s' % ('png' if thumbnail_ext == 'png' else 'jpeg')
            old_stream, new_stream = self.get_stream_number(
                filename, ('tags', 'mimetype'), mimetype)
            if old_stream is not None:
                options.extend(['-map', '-0:%d' % old_stream])
                new_stream -= 1
            options.extend([
                '-attach', thumbnail_filename,
                '-metadata:s:%d' % new_stream, 'mimetype=%s' % mimetype,
                '-metadata:s:%d' % new_stream, 'filename=cover.%s' % thumbnail_ext])

            self.to_screen('Adding thumbnail to "%s"' % filename)
            self.run_ffmpeg(filename, temp_filename, options)

        elif info['ext'] in ['m4a', 'mp4', 'mov']:
            try:
                options = ['-c', 'copy', '-map', '0', '-dn', '-map', '1']

                old_stream, new_stream = self.get_stream_number(
                    filename, ('disposition', 'attached_pic'), 1)
                if old_stream is not None:
                    options.extend(['-map', '-0:%d' % old_stream])
                    new_stream -= 1
                options.extend(['-disposition:%s' % new_stream, 'attached_pic'])

                self.to_screen('Adding thumbnail to "%s"' % filename)
                self.run_ffmpeg_multiple_files([filename, thumbnail_filename], temp_filename, options)

            except PostProcessingError as err:
                self.report_warning('unable to embed using ffprobe & ffmpeg; %s' % error_to_compat_str(err))
                atomicparsley = next((
                    x for x in ['AtomicParsley', 'atomicparsley']
                    if check_executable(x, ['-v'])), None)
                if atomicparsley is None:
                    raise EmbedThumbnailPPError('AtomicParsley was not found. Please install')

                cmd = [encodeFilename(atomicparsley, True),
                       encodeFilename(filename, True),
                       encodeArgument('--artwork'),
                       encodeFilename(thumbnail_filename, True),
                       encodeArgument('-o'),
                       encodeFilename(temp_filename, True)]
                cmd += [encodeArgument(o) for o in self._configuration_args('AtomicParsley')]

                self.to_screen('Adding thumbnail to "%s"' % filename)
                self.write_debug('AtomicParsley command line: %s' % shell_quote(cmd))
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process_communicate_or_kill(p)
                if p.returncode != 0:
                    msg = stderr.decode('utf-8', 'replace').strip()
                    raise EmbedThumbnailPPError(msg)
                # for formats that don't support thumbnails (like 3gp) AtomicParsley
                # won't create to the temporary file
                if b'No changes' in stdout:
                    self.report_warning('The file format doesn\'t support embedding a thumbnail')
                    success = False

        elif info['ext'] in ['ogg', 'opus']:
            if not has_mutagen:
                raise EmbedThumbnailPPError('module mutagen was not found. Please install using `python -m pip install mutagen`')
            self.to_screen('Adding thumbnail to "%s"' % filename)

            size_regex = r',\s*(?P<w>\d+)x(?P<h>\d+)\s*[,\[]'
            size_result = self.run_ffmpeg(thumbnail_filename, thumbnail_filename, ['-hide_banner'])
            mobj = re.search(size_regex, size_result)
            width, height = int(mobj.group('w')), int(mobj.group('h'))
            mimetype = ('image/%s' % ('png' if thumbnail_ext == 'png' else 'jpeg')).encode('ascii')

            # https://xiph.org/flac/format.html#metadata_block_picture
            data = bytearray()
            data += struct.pack('>II', 3, len(mimetype))
            data += mimetype
            data += struct.pack('>IIIIII', 0, width, height, 8, 0, os.stat(thumbnail_filename).st_size)  # 32 if png else 24

            fin = open(thumbnail_filename, "rb")
            data += fin.read()
            fin.close()

            temp_filename = filename
            f = mutagen.File(temp_filename)
            f.tags['METADATA_BLOCK_PICTURE'] = base64.b64encode(data).decode('ascii')
            f.save()

        else:
            raise EmbedThumbnailPPError('Supported filetypes for thumbnail embedding are: mp3, mkv/mka, ogg/opus, m4a/mp4/mov')

        if success and temp_filename != filename:
            os.remove(encodeFilename(filename))
            os.rename(encodeFilename(temp_filename), encodeFilename(filename))

        self.try_utime(filename, mtime, mtime)

        files_to_delete = [thumbnail_filename]
        if self._already_have_thumbnail:
            if original_thumbnail == thumbnail_filename:
                files_to_delete = []
        elif original_thumbnail != thumbnail_filename:
            files_to_delete.append(original_thumbnail)
        return files_to_delete, info
