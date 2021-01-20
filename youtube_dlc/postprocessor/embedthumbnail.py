# coding: utf-8
from __future__ import unicode_literals


import os
import subprocess

from .ffmpeg import FFmpegPostProcessor

from ..utils import (
    check_executable,
    encodeArgument,
    encodeFilename,
    PostProcessingError,
    prepend_extension,
    replace_extension,
    shell_quote,
    process_communicate_or_kill,
)


class EmbedThumbnailPPError(PostProcessingError):
    pass


class EmbedThumbnailPP(FFmpegPostProcessor):

    def __init__(self, downloader=None, already_have_thumbnail=False):
        super(EmbedThumbnailPP, self).__init__(downloader)
        self._already_have_thumbnail = already_have_thumbnail

    def run(self, info):
        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        if not info.get('thumbnails'):
            self.to_screen('There aren\'t any thumbnails to embed')
            return [], info

        thumbnail_filename = info['thumbnails'][-1]['filename']

        if not os.path.exists(encodeFilename(thumbnail_filename)):
            self.report_warning('Skipping embedding the thumbnail because the file is missing.')
            return [], info

        def is_webp(path):
            with open(encodeFilename(path), 'rb') as f:
                b = f.read(12)
            return b[0:4] == b'RIFF' and b[8:] == b'WEBP'

        # Correct extension for WebP file with wrong extension (see #25687, #25717)
        _, thumbnail_ext = os.path.splitext(thumbnail_filename)
        if thumbnail_ext:
            thumbnail_ext = thumbnail_ext[1:].lower()
            if thumbnail_ext != 'webp' and is_webp(thumbnail_filename):
                self.to_screen('Correcting extension to webp and escaping path for thumbnail "%s"' % thumbnail_filename)
                thumbnail_webp_filename = replace_extension(thumbnail_filename, 'webp')
                os.rename(encodeFilename(thumbnail_filename), encodeFilename(thumbnail_webp_filename))
                thumbnail_filename = thumbnail_webp_filename
                thumbnail_ext = 'webp'

        # Convert unsupported thumbnail formats to JPEG (see #25687, #25717)
        if thumbnail_ext not in ['jpg', 'png']:
            # NB: % is supposed to be escaped with %% but this does not work
            # for input files so working around with standard substitution
            escaped_thumbnail_filename = thumbnail_filename.replace('%', '#')
            os.rename(encodeFilename(thumbnail_filename), encodeFilename(escaped_thumbnail_filename))
            escaped_thumbnail_jpg_filename = replace_extension(escaped_thumbnail_filename, 'jpg')
            self.to_screen('Converting thumbnail "%s" to JPEG' % escaped_thumbnail_filename)
            self.run_ffmpeg(escaped_thumbnail_filename, escaped_thumbnail_jpg_filename, ['-bsf:v', 'mjpeg2jpeg'])
            os.remove(encodeFilename(escaped_thumbnail_filename))
            thumbnail_jpg_filename = replace_extension(thumbnail_filename, 'jpg')
            # Rename back to unescaped for further processing
            os.rename(encodeFilename(escaped_thumbnail_jpg_filename), encodeFilename(thumbnail_jpg_filename))
            thumbnail_filename = thumbnail_jpg_filename

        success = True
        if info['ext'] == 'mp3':
            options = [
                '-c', 'copy', '-map', '0:0', '-map', '1:0', '-id3v2_version', '3',
                '-metadata:s:v', 'title="Album cover"', '-metadata:s:v', 'comment="Cover (front)"']

            self.to_screen('Adding thumbnail to "%s"' % filename)
            self.run_ffmpeg_multiple_files([filename, thumbnail_filename], temp_filename, options)

        elif info['ext'] == 'mkv':
            options = [
                '-c', 'copy', '-map', '0', '-dn', '-attach', thumbnail_filename,
                '-metadata:s:t', 'mimetype=image/jpeg', '-metadata:s:t', 'filename=cover.jpg']

            self.to_screen('Adding thumbnail to "%s"' % filename)
            self.run_ffmpeg_multiple_files([filename], temp_filename, options)

        elif info['ext'] in ['m4a', 'mp4']:
            if not check_executable('AtomicParsley', ['-v']):
                raise EmbedThumbnailPPError('AtomicParsley was not found. Please install.')

            cmd = [encodeFilename('AtomicParsley', True),
                   encodeFilename(filename, True),
                   encodeArgument('--artwork'),
                   encodeFilename(thumbnail_filename, True),
                   encodeArgument('-o'),
                   encodeFilename(temp_filename, True)]
            cmd += [encodeArgument(o) for o in self._configuration_args(exe='AtomicParsley')]

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

        else:
            raise EmbedThumbnailPPError('Only mp3, mkv, m4a and mp4 are supported for thumbnail embedding for now.')

        if success:
            os.remove(encodeFilename(filename))
            os.rename(encodeFilename(temp_filename), encodeFilename(filename))

        files_to_delete = [] if self._already_have_thumbnail else [thumbnail_filename]
        return files_to_delete, info
