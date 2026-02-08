import base64
import os
import re
import subprocess

from .common import PostProcessor
from .ffmpeg import FFmpegPostProcessor, FFmpegThumbnailsConvertorPP
from ..compat import imghdr
from ..dependencies import mutagen
from ..utils import (
    Popen,
    PostProcessingError,
    check_executable,
    encodeArgument,
    prepend_extension,
    shell_quote,
)

if mutagen:
    from mutagen.flac import FLAC, Picture
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.oggopus import OggOpus
    from mutagen.oggvorbis import OggVorbis


class EmbedThumbnailPPError(PostProcessingError):
    pass


class EmbedThumbnailPP(FFmpegPostProcessor):

    def __init__(self, downloader=None, already_have_thumbnail=False):
        FFmpegPostProcessor.__init__(self, downloader)
        self._already_have_thumbnail = already_have_thumbnail

    def _get_thumbnail_resolution(self, filename, thumbnail_dict):
        def guess():
            width, height = thumbnail_dict.get('width'), thumbnail_dict.get('height')
            if width and height:
                return width, height

        try:
            size_regex = r',\s*(?P<w>\d+)x(?P<h>\d+)\s*[,\[]'
            size_result = self.run_ffmpeg(filename, None, ['-hide_banner'], expected_retcodes=(1,))
            mobj = re.search(size_regex, size_result)
            if mobj is None:
                return guess()
        except PostProcessingError as err:
            self.report_warning(f'unable to find the thumbnail resolution; {err}')
            return guess()
        return int(mobj.group('w')), int(mobj.group('h'))

    def _report_run(self, exe, filename):
        self.to_screen(f'{exe}: Adding thumbnail to "{filename}"')

    @PostProcessor._restrict_to(images=False)
    def run(self, info):
        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        if not info.get('thumbnails'):
            self.to_screen('There aren\'t any thumbnails to embed')
            return [], info

        idx = next((-i for i, t in enumerate(info['thumbnails'][::-1], 1) if t.get('filepath')), None)
        if idx is None:
            self.to_screen('There are no thumbnails on disk')
            return [], info
        thumbnail_filename = info['thumbnails'][idx]['filepath']
        if not os.path.exists(thumbnail_filename):
            self.report_warning('Skipping embedding the thumbnail because the file is missing.')
            return [], info

        # Correct extension for WebP file with wrong extension (see #25687, #25717)
        convertor = FFmpegThumbnailsConvertorPP(self._downloader)
        convertor.fixup_webp(info, idx)

        original_thumbnail = thumbnail_filename = info['thumbnails'][idx]['filepath']

        # Convert unsupported thumbnail formats (see #25687, #25717)
        # PNG is preferred since JPEG is lossy
        thumbnail_ext = os.path.splitext(thumbnail_filename)[1][1:]
        if info['ext'] not in ('mkv', 'mka') and thumbnail_ext not in ('jpg', 'jpeg', 'png'):
            thumbnail_filename = convertor.convert_thumbnail(thumbnail_filename, 'png')
            thumbnail_ext = 'png'

        mtime = os.stat(filename).st_mtime

        success = True
        if info['ext'] == 'mp3':
            options = [
                '-c', 'copy', '-map', '0:0', '-map', '1:0', '-write_id3v1', '1', '-id3v2_version', '3',
                '-metadata:s:v', 'title=Album cover', '-metadata:s:v', 'comment=Cover (front)']

            self._report_run('ffmpeg', filename)
            self.run_ffmpeg_multiple_files([filename, thumbnail_filename], temp_filename, options)

        elif info['ext'] in ['mkv', 'mka']:
            options = list(self.stream_copy_opts())

            mimetype = f'image/{thumbnail_ext.replace("jpg", "jpeg")}'
            old_stream, new_stream = self.get_stream_number(
                filename, ('tags', 'mimetype'), mimetype)
            if old_stream is not None:
                options.extend(['-map', f'-0:{old_stream}'])
                new_stream -= 1
            options.extend([
                '-attach', self._ffmpeg_filename_argument(thumbnail_filename),
                f'-metadata:s:{new_stream}', f'mimetype={mimetype}',
                f'-metadata:s:{new_stream}', f'filename=cover.{thumbnail_ext}'])

            self._report_run('ffmpeg', filename)
            self.run_ffmpeg(filename, temp_filename, options)

        elif info['ext'] in ['m4a', 'mp4', 'm4v', 'mov']:
            prefer_atomicparsley = 'embed-thumbnail-atomicparsley' in self.get_param('compat_opts', [])
            # Method 1: Use mutagen
            if not mutagen or prefer_atomicparsley:
                success = False
            else:
                self._report_run('mutagen', filename)
                f = {'jpeg': MP4Cover.FORMAT_JPEG, 'png': MP4Cover.FORMAT_PNG}
                try:
                    with open(thumbnail_filename, 'rb') as thumbfile:
                        thumb_data = thumbfile.read()

                    type_ = imghdr.what(h=thumb_data)
                    if not type_:
                        raise ValueError('could not determine image type')
                    elif type_ not in f:
                        raise ValueError(f'incompatible image type: {type_}')

                    meta = MP4(filename)
                    # NOTE: the 'covr' atom is a non-standard MPEG-4 atom,
                    # Apple iTunes 'M4A' files include the 'moov.udta.meta.ilst' atom.
                    meta.tags['covr'] = [MP4Cover(data=thumb_data, imageformat=f[type_])]
                    meta.save()
                    temp_filename = filename
                except Exception as err:
                    self.report_warning(f'unable to embed using mutagen; {err}')
                    success = False

            # Method 2: Use AtomicParsley
            if not success:
                success = True
                atomicparsley = next((
                    # libatomicparsley.so : See https://github.com/xibr/ytdlp-lazy/issues/1
                    x for x in ['AtomicParsley', 'atomicparsley', 'libatomicparsley.so']
                    if check_executable(x, ['-v'])), None)
                if atomicparsley is None:
                    self.to_screen('Neither mutagen nor AtomicParsley was found. Falling back to ffmpeg')
                    success = False
                else:
                    if not prefer_atomicparsley:
                        self.to_screen('mutagen was not found. Falling back to AtomicParsley')
                    cmd = [atomicparsley,
                           filename,
                           encodeArgument('--artwork'),
                           thumbnail_filename,
                           encodeArgument('-o'),
                           temp_filename]
                    cmd += [encodeArgument(o) for o in self._configuration_args('AtomicParsley')]

                    self._report_run('atomicparsley', filename)
                    self.write_debug(f'AtomicParsley command line: {shell_quote(cmd)}')
                    stdout, stderr, returncode = Popen.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if returncode:
                        self.report_warning(f'Unable to embed thumbnails using AtomicParsley; {stderr.strip()}')
                        success = False
                    # for formats that don't support thumbnails (like 3gp) AtomicParsley
                    # won't create to the temporary file
                    elif 'No changes' in stdout:
                        self.report_warning('The file format doesn\'t support embedding a thumbnail')
                        success = False

            # Method 3: Use ffmpeg+ffprobe
            # Thumbnails attached using this method doesn't show up as cover in some cases
            # See https://github.com/yt-dlp/yt-dlp/issues/2125, https://github.com/yt-dlp/yt-dlp/issues/411
            if not success:
                success = True
                try:
                    options = [*self.stream_copy_opts(), '-map', '1']

                    old_stream, new_stream = self.get_stream_number(
                        filename, ('disposition', 'attached_pic'), 1)
                    if old_stream is not None:
                        options.extend(['-map', f'-0:{old_stream}'])
                        new_stream -= 1
                    options.extend([f'-disposition:{new_stream}', 'attached_pic'])

                    self._report_run('ffmpeg', filename)
                    self.run_ffmpeg_multiple_files([filename, thumbnail_filename], temp_filename, options)
                except PostProcessingError as err:
                    success = False
                    raise EmbedThumbnailPPError(f'Unable to embed using ffprobe & ffmpeg; {err}')

        elif info['ext'] in ['ogg', 'opus', 'flac']:
            if not mutagen:
                raise EmbedThumbnailPPError('module mutagen was not found. Please install using `python3 -m pip install mutagen`')

            self._report_run('mutagen', filename)
            f = {'opus': OggOpus, 'flac': FLAC, 'ogg': OggVorbis}[info['ext']](filename)

            pic = Picture()
            pic.mime = f'image/{imghdr.what(thumbnail_filename)}'
            with open(thumbnail_filename, 'rb') as thumbfile:
                pic.data = thumbfile.read()
            pic.type = 3  # front cover
            res = self._get_thumbnail_resolution(thumbnail_filename, info['thumbnails'][idx])
            if res is not None:
                pic.width, pic.height = res

            if info['ext'] == 'flac':
                f.add_picture(pic)
            else:
                # https://wiki.xiph.org/VorbisComment#METADATA_BLOCK_PICTURE
                f['METADATA_BLOCK_PICTURE'] = base64.b64encode(pic.write()).decode('ascii')
            f.save()
            temp_filename = filename

        else:
            raise EmbedThumbnailPPError('Supported filetypes for thumbnail embedding are: mp3, mkv/mka, ogg/opus/flac, m4a/mp4/m4v/mov')

        if success and temp_filename != filename:
            os.replace(temp_filename, filename)

        self.try_utime(filename, mtime, mtime)
        converted = original_thumbnail != thumbnail_filename
        self._delete_downloaded_files(
            thumbnail_filename if converted or not self._already_have_thumbnail else None,
            original_thumbnail if converted and not self._already_have_thumbnail else None,
            info=info)
        return [], info
