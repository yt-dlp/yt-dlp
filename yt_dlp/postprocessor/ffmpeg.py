from __future__ import unicode_literals

import io
import os
import subprocess
import time
import re
import json


from .common import AudioConversionError, PostProcessor

from ..compat import compat_str, compat_numeric_types
from ..utils import (
    encodeArgument,
    encodeFilename,
    get_exe_version,
    is_outdated_version,
    PostProcessingError,
    prepend_extension,
    shell_quote,
    dfxp2srt,
    ISO639Utils,
    process_communicate_or_kill,
    replace_extension,
    traverse_dict,
)


EXT_TO_OUT_FORMATS = {
    'aac': 'adts',
    'flac': 'flac',
    'm4a': 'ipod',
    'mka': 'matroska',
    'mkv': 'matroska',
    'mpg': 'mpeg',
    'ogv': 'ogg',
    'ts': 'mpegts',
    'wma': 'asf',
    'wmv': 'asf',
}
ACODECS = {
    'mp3': 'libmp3lame',
    'aac': 'aac',
    'flac': 'flac',
    'm4a': 'aac',
    'opus': 'libopus',
    'vorbis': 'libvorbis',
    'wav': None,
}


class FFmpegPostProcessorError(PostProcessingError):
    pass


class FFmpegPostProcessor(PostProcessor):
    def __init__(self, downloader=None):
        PostProcessor.__init__(self, downloader)
        self._determine_executables()

    def check_version(self):
        if not self.available:
            raise FFmpegPostProcessorError('ffmpeg not found. Please install or provide the path using --ffmpeg-location')

        required_version = '10-0' if self.basename == 'avconv' else '1.0'
        if is_outdated_version(
                self._versions[self.basename], required_version):
            warning = 'Your copy of %s is outdated, update %s to version %s or newer if you encounter any errors.' % (
                self.basename, self.basename, required_version)
            self.report_warning(warning)

    @staticmethod
    def get_versions(downloader=None):
        return FFmpegPostProcessor(downloader)._versions

    def _determine_executables(self):
        programs = ['avprobe', 'avconv', 'ffmpeg', 'ffprobe']
        prefer_ffmpeg = True

        def get_ffmpeg_version(path):
            ver = get_exe_version(path, args=['-version'])
            if ver:
                regexs = [
                    r'(?:\d+:)?([0-9.]+)-[0-9]+ubuntu[0-9.]+$',  # Ubuntu, see [1]
                    r'n([0-9.]+)$',  # Arch Linux
                    # 1. http://www.ducea.com/2006/06/17/ubuntu-package-version-naming-explanation/
                ]
                for regex in regexs:
                    mobj = re.match(regex, ver)
                    if mobj:
                        ver = mobj.group(1)
            return ver

        self.basename = None
        self.probe_basename = None

        self._paths = None
        self._versions = None
        if self._downloader:
            prefer_ffmpeg = self.get_param('prefer_ffmpeg', True)
            location = self.get_param('ffmpeg_location')
            if location is not None:
                if not os.path.exists(location):
                    self.report_warning(
                        'ffmpeg-location %s does not exist! '
                        'Continuing without ffmpeg.' % (location))
                    self._versions = {}
                    return
                elif not os.path.isdir(location):
                    basename = os.path.splitext(os.path.basename(location))[0]
                    if basename not in programs:
                        self.report_warning(
                            'Cannot identify executable %s, its basename should be one of %s. '
                            'Continuing without ffmpeg.' %
                            (location, ', '.join(programs)))
                        self._versions = {}
                        return None
                    location = os.path.dirname(os.path.abspath(location))
                    if basename in ('ffmpeg', 'ffprobe'):
                        prefer_ffmpeg = True

                self._paths = dict(
                    (p, os.path.join(location, p)) for p in programs)
                self._versions = dict(
                    (p, get_ffmpeg_version(self._paths[p])) for p in programs)
        if self._versions is None:
            self._versions = dict(
                (p, get_ffmpeg_version(p)) for p in programs)
            self._paths = dict((p, p) for p in programs)

        if prefer_ffmpeg is False:
            prefs = ('avconv', 'ffmpeg')
        else:
            prefs = ('ffmpeg', 'avconv')
        for p in prefs:
            if self._versions[p]:
                self.basename = p
                break

        if prefer_ffmpeg is False:
            prefs = ('avprobe', 'ffprobe')
        else:
            prefs = ('ffprobe', 'avprobe')
        for p in prefs:
            if self._versions[p]:
                self.probe_basename = p
                break

    @property
    def available(self):
        return self.basename is not None

    @property
    def executable(self):
        return self._paths[self.basename]

    @property
    def probe_available(self):
        return self.probe_basename is not None

    @property
    def probe_executable(self):
        return self._paths[self.probe_basename]

    def get_audio_codec(self, path):
        if not self.probe_available and not self.available:
            raise PostProcessingError('ffprobe and ffmpeg not found. Please install or provide the path using --ffmpeg-location')
        try:
            if self.probe_available:
                cmd = [
                    encodeFilename(self.probe_executable, True),
                    encodeArgument('-show_streams')]
            else:
                cmd = [
                    encodeFilename(self.executable, True),
                    encodeArgument('-i')]
            cmd.append(encodeFilename(self._ffmpeg_filename_argument(path), True))
            self.write_debug('%s command line: %s' % (self.basename, shell_quote(cmd)))
            handle = subprocess.Popen(
                cmd, stderr=subprocess.PIPE,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            stdout_data, stderr_data = process_communicate_or_kill(handle)
            expected_ret = 0 if self.probe_available else 1
            if handle.wait() != expected_ret:
                return None
        except (IOError, OSError):
            return None
        output = (stdout_data if self.probe_available else stderr_data).decode('ascii', 'ignore')
        if self.probe_available:
            audio_codec = None
            for line in output.split('\n'):
                if line.startswith('codec_name='):
                    audio_codec = line.split('=')[1].strip()
                elif line.strip() == 'codec_type=audio' and audio_codec is not None:
                    return audio_codec
        else:
            # Stream #FILE_INDEX:STREAM_INDEX[STREAM_ID](LANGUAGE): CODEC_TYPE: CODEC_NAME
            mobj = re.search(
                r'Stream\s*#\d+:\d+(?:\[0x[0-9a-f]+\])?(?:\([a-z]{3}\))?:\s*Audio:\s*([0-9a-z]+)',
                output)
            if mobj:
                return mobj.group(1)
        return None

    def get_metadata_object(self, path, opts=[]):
        if self.probe_basename != 'ffprobe':
            if self.probe_available:
                self.report_warning('Only ffprobe is supported for metadata extraction')
            raise PostProcessingError('ffprobe not found. Please install or provide the path using --ffmpeg-location')
        self.check_version()

        cmd = [
            encodeFilename(self.probe_executable, True),
            encodeArgument('-hide_banner'),
            encodeArgument('-show_format'),
            encodeArgument('-show_streams'),
            encodeArgument('-print_format'),
            encodeArgument('json'),
        ]

        cmd += opts
        cmd.append(encodeFilename(self._ffmpeg_filename_argument(path), True))
        self.write_debug('ffprobe command line: %s' % shell_quote(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout, stderr = p.communicate()
        return json.loads(stdout.decode('utf-8', 'replace'))

    def get_stream_number(self, path, keys, value):
        streams = self.get_metadata_object(path)['streams']
        num = next(
            (i for i, stream in enumerate(streams) if traverse_dict(stream, keys, casesense=False) == value),
            None)
        return num, len(streams)

    def run_ffmpeg_multiple_files(self, input_paths, out_path, opts):
        return self.real_run_ffmpeg(
            [(path, []) for path in input_paths],
            [(out_path, opts)])

    def real_run_ffmpeg(self, input_path_opts, output_path_opts):
        self.check_version()

        oldest_mtime = min(
            os.stat(encodeFilename(path)).st_mtime for path, _ in input_path_opts)

        cmd = [encodeFilename(self.executable, True), encodeArgument('-y')]
        # avconv does not have repeat option
        if self.basename == 'ffmpeg':
            cmd += [encodeArgument('-loglevel'), encodeArgument('repeat+info')]

        def make_args(file, args, name, number):
            keys = ['_%s%d' % (name, number), '_%s' % name]
            if name == 'o' and number == 1:
                keys.append('')
            args += self._configuration_args(self.basename, keys)
            if name == 'i':
                args.append('-i')
            return (
                [encodeArgument(arg) for arg in args]
                + [encodeFilename(self._ffmpeg_filename_argument(file), True)])

        for arg_type, path_opts in (('i', input_path_opts), ('o', output_path_opts)):
            cmd += [arg for i, o in enumerate(path_opts)
                    for arg in make_args(o[0], o[1], arg_type, i + 1)]

        self.write_debug('ffmpeg command line: %s' % shell_quote(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout, stderr = process_communicate_or_kill(p)
        if p.returncode != 0:
            stderr = stderr.decode('utf-8', 'replace').strip()
            if self.get_param('verbose', False):
                self.report_error(stderr)
            raise FFmpegPostProcessorError(stderr.split('\n')[-1])
        for out_path, _ in output_path_opts:
            self.try_utime(out_path, oldest_mtime, oldest_mtime)
        return stderr.decode('utf-8', 'replace')

    def run_ffmpeg(self, path, out_path, opts):
        return self.run_ffmpeg_multiple_files([path], out_path, opts)

    def _ffmpeg_filename_argument(self, fn):
        # Always use 'file:' because the filename may contain ':' (ffmpeg
        # interprets that as a protocol) or can start with '-' (-- is broken in
        # ffmpeg, see https://ffmpeg.org/trac/ffmpeg/ticket/2127 for details)
        # Also leave '-' intact in order not to break streaming to stdout.
        if fn.startswith(('http://', 'https://')):
            return fn
        return 'file:' + fn if fn != '-' else fn


class FFmpegExtractAudioPP(FFmpegPostProcessor):
    COMMON_AUDIO_EXTENSIONS = ('wav', 'flac', 'm4a', 'aiff', 'mp3', 'ogg', 'mka', 'opus', 'wma')

    def __init__(self, downloader=None, preferredcodec=None, preferredquality=None, nopostoverwrites=False):
        FFmpegPostProcessor.__init__(self, downloader)
        if preferredcodec is None:
            preferredcodec = 'best'
        self._preferredcodec = preferredcodec
        self._preferredquality = preferredquality
        self._nopostoverwrites = nopostoverwrites

    def run_ffmpeg(self, path, out_path, codec, more_opts):
        if codec is None:
            acodec_opts = []
        else:
            acodec_opts = ['-acodec', codec]
        opts = ['-vn'] + acodec_opts + more_opts
        try:
            FFmpegPostProcessor.run_ffmpeg(self, path, out_path, opts)
        except FFmpegPostProcessorError as err:
            raise AudioConversionError(err.msg)

    def run(self, information):
        path = information['filepath']
        orig_ext = information['ext']

        if self._preferredcodec == 'best' and orig_ext in self.COMMON_AUDIO_EXTENSIONS:
            self.to_screen('Skipping audio extraction since the file is already in a common audio format')
            return [], information

        filecodec = self.get_audio_codec(path)
        if filecodec is None:
            raise PostProcessingError('WARNING: unable to obtain file audio codec with ffprobe')

        more_opts = []
        if self._preferredcodec == 'best' or self._preferredcodec == filecodec or (self._preferredcodec == 'm4a' and filecodec == 'aac'):
            if filecodec == 'aac' and self._preferredcodec in ['m4a', 'best']:
                # Lossless, but in another container
                acodec = 'copy'
                extension = 'm4a'
                more_opts = ['-bsf:a', 'aac_adtstoasc']
            elif filecodec in ['aac', 'flac', 'mp3', 'vorbis', 'opus']:
                # Lossless if possible
                acodec = 'copy'
                extension = filecodec
                if filecodec == 'aac':
                    more_opts = ['-f', 'adts']
                if filecodec == 'vorbis':
                    extension = 'ogg'
            else:
                # MP3 otherwise.
                acodec = 'libmp3lame'
                extension = 'mp3'
                more_opts = []
                if self._preferredquality is not None:
                    if int(self._preferredquality) < 10:
                        more_opts += ['-q:a', self._preferredquality]
                    else:
                        more_opts += ['-b:a', self._preferredquality + 'k']
        else:
            # We convert the audio (lossy if codec is lossy)
            acodec = ACODECS[self._preferredcodec]
            extension = self._preferredcodec
            more_opts = []
            if self._preferredquality is not None:
                # The opus codec doesn't support the -aq option
                if int(self._preferredquality) < 10 and extension != 'opus':
                    more_opts += ['-q:a', self._preferredquality]
                else:
                    more_opts += ['-b:a', self._preferredquality + 'k']
            if self._preferredcodec == 'aac':
                more_opts += ['-f', 'adts']
            if self._preferredcodec == 'm4a':
                more_opts += ['-bsf:a', 'aac_adtstoasc']
            if self._preferredcodec == 'vorbis':
                extension = 'ogg'
            if self._preferredcodec == 'wav':
                extension = 'wav'
                more_opts += ['-f', 'wav']

        prefix, sep, ext = path.rpartition('.')  # not os.path.splitext, since the latter does not work on unicode in all setups
        new_path = prefix + sep + extension

        information['filepath'] = new_path
        information['ext'] = extension

        # If we download foo.mp3 and convert it to... foo.mp3, then don't delete foo.mp3, silly.
        if (new_path == path
                or (self._nopostoverwrites and os.path.exists(encodeFilename(new_path)))):
            self.to_screen('Post-process file %s exists, skipping' % new_path)
            return [], information

        try:
            self.to_screen('Destination: ' + new_path)
            self.run_ffmpeg(path, new_path, acodec, more_opts)
        except AudioConversionError as e:
            raise PostProcessingError(
                'audio conversion failed: ' + e.msg)
        except Exception:
            raise PostProcessingError('error running ' + self.basename)

        # Try to update the date time for extracted audio file.
        if information.get('filetime') is not None:
            self.try_utime(
                new_path, time.time(), information['filetime'],
                errnote='Cannot update utime of audio file')

        return [path], information


class FFmpegVideoRemuxerPP(FFmpegPostProcessor):
    def __init__(self, downloader=None, preferedformat=None):
        super(FFmpegVideoRemuxerPP, self).__init__(downloader)
        self._preferedformats = preferedformat.lower().split('/')

    def run(self, information):
        path = information['filepath']
        sourceext, targetext = information['ext'].lower(), None
        for pair in self._preferedformats:
            kv = pair.split('>')
            if len(kv) == 1 or kv[0].strip() == sourceext:
                targetext = kv[-1].strip()
                break

        _skip_msg = (
            'could not find a mapping for %s' if not targetext
            else 'already is in target format %s' if sourceext == targetext
            else None)
        if _skip_msg:
            self.to_screen('Not remuxing media file %s; %s' % (path, _skip_msg % sourceext))
            return [], information

        options = ['-c', 'copy', '-map', '0', '-dn']
        if targetext in ['mp4', 'm4a', 'mov']:
            options.extend(['-movflags', '+faststart'])
        prefix, sep, oldext = path.rpartition('.')
        outpath = prefix + sep + targetext
        self.to_screen('Remuxing video from %s to %s; Destination: %s' % (sourceext, targetext, outpath))
        self.run_ffmpeg(path, outpath, options)
        information['filepath'] = outpath
        information['format'] = targetext
        information['ext'] = targetext
        return [path], information


class FFmpegVideoConvertorPP(FFmpegPostProcessor):
    def __init__(self, downloader=None, preferedformat=None):
        super(FFmpegVideoConvertorPP, self).__init__(downloader)
        self._preferedformat = preferedformat

    def run(self, information):
        path = information['filepath']
        if information['ext'] == self._preferedformat:
            self.to_screen('Not converting video file %s - already is in target format %s' % (path, self._preferedformat))
            return [], information
        options = []
        if self._preferedformat == 'avi':
            options.extend(['-c:v', 'libxvid', '-vtag', 'XVID'])
        prefix, sep, ext = path.rpartition('.')
        outpath = prefix + sep + self._preferedformat
        self.to_screen('Converting video from %s to %s, Destination: ' % (information['ext'], self._preferedformat) + outpath)
        self.run_ffmpeg(path, outpath, options)
        information['filepath'] = outpath
        information['format'] = self._preferedformat
        information['ext'] = self._preferedformat
        return [path], information


class FFmpegEmbedSubtitlePP(FFmpegPostProcessor):
    def __init__(self, downloader=None, already_have_subtitle=False):
        super(FFmpegEmbedSubtitlePP, self).__init__(downloader)
        self._already_have_subtitle = already_have_subtitle

    def run(self, information):
        if information['ext'] not in ('mp4', 'webm', 'mkv'):
            self.to_screen('Subtitles can only be embedded in mp4, webm or mkv files')
            return [], information
        subtitles = information.get('requested_subtitles')
        if not subtitles:
            self.to_screen('There aren\'t any subtitles to embed')
            return [], information

        filename = information['filepath']

        ext = information['ext']
        sub_langs = []
        sub_filenames = []
        webm_vtt_warn = False
        mp4_ass_warn = False

        for lang, sub_info in subtitles.items():
            sub_ext = sub_info['ext']
            if sub_ext == 'json':
                self.report_warning('JSON subtitles cannot be embedded')
            elif ext != 'webm' or ext == 'webm' and sub_ext == 'vtt':
                sub_langs.append(lang)
                sub_filenames.append(sub_info['filepath'])
            else:
                if not webm_vtt_warn and ext == 'webm' and sub_ext != 'vtt':
                    webm_vtt_warn = True
                    self.report_warning('Only WebVTT subtitles can be embedded in webm files')
            if not mp4_ass_warn and ext == 'mp4' and sub_ext == 'ass':
                mp4_ass_warn = True
                self.report_warning('ASS subtitles cannot be properly embedded in mp4 files; expect issues')

        if not sub_langs:
            return [], information

        input_files = [filename] + sub_filenames

        opts = [
            '-c', 'copy', '-map', '0', '-dn',
            # Don't copy the existing subtitles, we may be running the
            # postprocessor a second time
            '-map', '-0:s',
            # Don't copy Apple TV chapters track, bin_data (see #19042, #19024,
            # https://trac.ffmpeg.org/ticket/6016)
            '-map', '-0:d',
        ]
        if information['ext'] == 'mp4':
            opts += ['-c:s', 'mov_text']
        for (i, lang) in enumerate(sub_langs):
            opts.extend(['-map', '%d:0' % (i + 1)])
            lang_code = ISO639Utils.short2long(lang) or lang
            opts.extend(['-metadata:s:s:%d' % i, 'language=%s' % lang_code])

        temp_filename = prepend_extension(filename, 'temp')
        self.to_screen('Embedding subtitles in "%s"' % filename)
        self.run_ffmpeg_multiple_files(input_files, temp_filename, opts)
        os.remove(encodeFilename(filename))
        os.rename(encodeFilename(temp_filename), encodeFilename(filename))

        files_to_delete = [] if self._already_have_subtitle else sub_filenames
        return files_to_delete, information


class FFmpegMetadataPP(FFmpegPostProcessor):
    def run(self, info):
        metadata = {}

        def add(meta_list, info_list=None):
            if not meta_list:
                return
            if not info_list:
                info_list = meta_list
            if not isinstance(meta_list, (list, tuple)):
                meta_list = (meta_list,)
            if not isinstance(info_list, (list, tuple)):
                info_list = (info_list,)
            for info_f in info_list:
                if isinstance(info.get(info_f), (compat_str, compat_numeric_types)):
                    for meta_f in meta_list:
                        metadata[meta_f] = info[info_f]
                    break

        # See [1-4] for some info on media metadata/metadata supported
        # by ffmpeg.
        # 1. https://kdenlive.org/en/project/adding-meta-data-to-mp4-video/
        # 2. https://wiki.multimedia.cx/index.php/FFmpeg_Metadata
        # 3. https://kodi.wiki/view/Video_file_tagging

        add('title', ('track', 'title'))
        add('date', 'upload_date')
        add(('description', 'synopsis'), 'description')
        add(('purl', 'comment'), 'webpage_url')
        add('track', 'track_number')
        add('artist', ('artist', 'creator', 'uploader', 'uploader_id'))
        add('genre')
        add('album')
        add('album_artist')
        add('disc', 'disc_number')
        add('show', 'series')
        add('season_number')
        add('episode_id', ('episode', 'episode_id'))
        add('episode_sort', 'episode_number')

        prefix = 'meta_'
        for key in filter(lambda k: k.startswith(prefix), info.keys()):
            add(key[len(prefix):], key)

        if not metadata:
            self.to_screen('There isn\'t any metadata to add')
            return [], info

        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')
        in_filenames = [filename]
        options = ['-map', '0', '-dn']

        if info['ext'] == 'm4a':
            options.extend(['-vn', '-acodec', 'copy'])
        else:
            options.extend(['-c', 'copy'])

        for name, value in metadata.items():
            options.extend(['-metadata', '%s=%s' % (name, value)])

        chapters = info.get('chapters', [])
        if chapters:
            metadata_filename = replace_extension(filename, 'meta')
            with io.open(metadata_filename, 'wt', encoding='utf-8') as f:
                def ffmpeg_escape(text):
                    return re.sub(r'(=|;|#|\\|\n)', r'\\\1', text)

                metadata_file_content = ';FFMETADATA1\n'
                for chapter in chapters:
                    metadata_file_content += '[CHAPTER]\nTIMEBASE=1/1000\n'
                    metadata_file_content += 'START=%d\n' % (chapter['start_time'] * 1000)
                    metadata_file_content += 'END=%d\n' % (chapter['end_time'] * 1000)
                    chapter_title = chapter.get('title')
                    if chapter_title:
                        metadata_file_content += 'title=%s\n' % ffmpeg_escape(chapter_title)
                f.write(metadata_file_content)
                in_filenames.append(metadata_filename)
                options.extend(['-map_metadata', '1'])

        if '__infojson_filename' in info and info['ext'] in ('mkv', 'mka'):
            old_stream, new_stream = self.get_stream_number(
                filename, ('tags', 'mimetype'), 'application/json')
            if old_stream is not None:
                options.extend(['-map', '-0:%d' % old_stream])
                new_stream -= 1

            options.extend([
                '-attach', info['__infojson_filename'],
                '-metadata:s:%d' % new_stream, 'mimetype=application/json'
            ])

        self.to_screen('Adding metadata to \'%s\'' % filename)
        self.run_ffmpeg_multiple_files(in_filenames, temp_filename, options)
        if chapters:
            os.remove(metadata_filename)
        os.remove(encodeFilename(filename))
        os.rename(encodeFilename(temp_filename), encodeFilename(filename))
        return [], info


class FFmpegMergerPP(FFmpegPostProcessor):
    def run(self, info):
        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')
        args = ['-c', 'copy']
        for (i, fmt) in enumerate(info['requested_formats']):
            if fmt.get('acodec') != 'none':
                args.extend(['-map', '%u:a:0' % (i)])
            if fmt.get('vcodec') != 'none':
                args.extend(['-map', '%u:v:0' % (i)])
        self.to_screen('Merging formats into "%s"' % filename)
        self.run_ffmpeg_multiple_files(info['__files_to_merge'], temp_filename, args)
        os.rename(encodeFilename(temp_filename), encodeFilename(filename))
        return info['__files_to_merge'], info

    def can_merge(self):
        # TODO: figure out merge-capable ffmpeg version
        if self.basename != 'avconv':
            return True

        required_version = '10-0'
        if is_outdated_version(
                self._versions[self.basename], required_version):
            warning = ('Your copy of %s is outdated and unable to properly mux separate video and audio files, '
                       'yt-dlp will download single file media. '
                       'Update %s to version %s or newer to fix this.') % (
                           self.basename, self.basename, required_version)
            self.report_warning(warning)
            return False
        return True


class FFmpegFixupStretchedPP(FFmpegPostProcessor):
    def run(self, info):
        stretched_ratio = info.get('stretched_ratio')
        if stretched_ratio is None or stretched_ratio == 1:
            return [], info

        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        options = ['-c', 'copy', '-map', '0', '-dn', '-aspect', '%f' % stretched_ratio]
        self.to_screen('Fixing aspect ratio in "%s"' % filename)
        self.run_ffmpeg(filename, temp_filename, options)

        os.remove(encodeFilename(filename))
        os.rename(encodeFilename(temp_filename), encodeFilename(filename))

        return [], info


class FFmpegFixupM4aPP(FFmpegPostProcessor):
    def run(self, info):
        if info.get('container') != 'm4a_dash':
            return [], info

        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        options = ['-c', 'copy', '-map', '0', '-dn', '-f', 'mp4']
        self.to_screen('Correcting container in "%s"' % filename)
        self.run_ffmpeg(filename, temp_filename, options)

        os.remove(encodeFilename(filename))
        os.rename(encodeFilename(temp_filename), encodeFilename(filename))

        return [], info


class FFmpegFixupM3u8PP(FFmpegPostProcessor):
    def run(self, info):
        filename = info['filepath']
        if self.get_audio_codec(filename) == 'aac':
            temp_filename = prepend_extension(filename, 'temp')

            options = ['-c', 'copy', '-map', '0', '-dn', '-f', 'mp4', '-bsf:a', 'aac_adtstoasc']
            self.to_screen('Fixing malformed AAC bitstream in "%s"' % filename)
            self.run_ffmpeg(filename, temp_filename, options)

            os.remove(encodeFilename(filename))
            os.rename(encodeFilename(temp_filename), encodeFilename(filename))
        return [], info


class FFmpegSubtitlesConvertorPP(FFmpegPostProcessor):
    def __init__(self, downloader=None, format=None):
        super(FFmpegSubtitlesConvertorPP, self).__init__(downloader)
        self.format = format

    def run(self, info):
        subs = info.get('requested_subtitles')
        new_ext = self.format
        new_format = new_ext
        if new_format == 'vtt':
            new_format = 'webvtt'
        if subs is None:
            self.to_screen('There aren\'t any subtitles to convert')
            return [], info
        self.to_screen('Converting subtitles')
        sub_filenames = []
        for lang, sub in subs.items():
            ext = sub['ext']
            if ext == new_ext:
                self.to_screen('Subtitle file for %s is already in the requested format' % new_ext)
                continue
            elif ext == 'json':
                self.to_screen(
                    'You have requested to convert json subtitles into another format, '
                    'which is currently not possible')
                continue
            old_file = sub['filepath']
            sub_filenames.append(old_file)
            new_file = replace_extension(old_file, new_ext)

            if ext in ('dfxp', 'ttml', 'tt'):
                self.report_warning(
                    'You have requested to convert dfxp (TTML) subtitles into another format, '
                    'which results in style information loss')

                dfxp_file = old_file
                srt_file = replace_extension(old_file, 'srt')

                with open(dfxp_file, 'rb') as f:
                    srt_data = dfxp2srt(f.read())

                with io.open(srt_file, 'wt', encoding='utf-8') as f:
                    f.write(srt_data)
                old_file = srt_file

                subs[lang] = {
                    'ext': 'srt',
                    'data': srt_data,
                    'filepath': srt_file,
                }

                if new_ext == 'srt':
                    continue
                else:
                    sub_filenames.append(srt_file)

            self.run_ffmpeg(old_file, new_file, ['-f', new_format])

            with io.open(new_file, 'rt', encoding='utf-8') as f:
                subs[lang] = {
                    'ext': new_ext,
                    'data': f.read(),
                    'filepath': new_file,
                }

            info['__files_to_move'][new_file] = replace_extension(
                info['__files_to_move'][old_file], new_ext)

        return sub_filenames, info


class FFmpegSplitChaptersPP(FFmpegPostProcessor):

    def _prepare_filename(self, number, chapter, info):
        info = info.copy()
        info.update({
            'section_number': number,
            'section_title': chapter.get('title'),
            'section_start': chapter.get('start_time'),
            'section_end': chapter.get('end_time'),
        })
        return self._downloader.prepare_filename(info, 'chapter')

    def _ffmpeg_args_for_chapter(self, number, chapter, info):
        destination = self._prepare_filename(number, chapter, info)
        if not self._downloader._ensure_dir_exists(encodeFilename(destination)):
            return

        chapter['filepath'] = destination
        self.to_screen('Chapter %03d; Destination: %s' % (number, destination))
        return (
            destination,
            ['-ss', compat_str(chapter['start_time']),
             '-t', compat_str(chapter['end_time'] - chapter['start_time'])])

    def run(self, info):
        chapters = info.get('chapters') or []
        if not chapters:
            self.report_warning('Chapter information is unavailable')
            return [], info

        self.to_screen('Splitting video by chapters; %d chapters found' % len(chapters))
        for idx, chapter in enumerate(chapters):
            destination, opts = self._ffmpeg_args_for_chapter(idx + 1, chapter, info)
            self.real_run_ffmpeg([(info['filepath'], opts)], [(destination, ['-c', 'copy'])])
        return [], info


class FFmpegThumbnailsConvertorPP(FFmpegPostProcessor):
    def __init__(self, downloader=None, format=None):
        super(FFmpegThumbnailsConvertorPP, self).__init__(downloader)
        self.format = format

    @staticmethod
    def is_webp(path):
        with open(encodeFilename(path), 'rb') as f:
            b = f.read(12)
        return b[0:4] == b'RIFF' and b[8:] == b'WEBP'

    def fixup_webp(self, info, idx=-1):
        thumbnail_filename = info['thumbnails'][idx]['filepath']
        _, thumbnail_ext = os.path.splitext(thumbnail_filename)
        if thumbnail_ext:
            thumbnail_ext = thumbnail_ext[1:].lower()
            if thumbnail_ext != 'webp' and self.is_webp(thumbnail_filename):
                self.to_screen('Correcting thumbnail "%s" extension to webp' % thumbnail_filename)
                webp_filename = replace_extension(thumbnail_filename, 'webp')
                if os.path.exists(webp_filename):
                    os.remove(webp_filename)
                os.rename(encodeFilename(thumbnail_filename), encodeFilename(webp_filename))
                info['thumbnails'][idx]['filepath'] = webp_filename
                info['__files_to_move'][webp_filename] = replace_extension(
                    info['__files_to_move'].pop(thumbnail_filename), 'webp')

    def convert_thumbnail(self, thumbnail_filename, ext):
        if ext != 'jpg':
            raise FFmpegPostProcessorError('Only conversion to jpg is currently supported')
        # NB: % is supposed to be escaped with %% but this does not work
        # for input files so working around with standard substitution
        escaped_thumbnail_filename = thumbnail_filename.replace('%', '#')
        os.rename(encodeFilename(thumbnail_filename), encodeFilename(escaped_thumbnail_filename))
        escaped_thumbnail_jpg_filename = replace_extension(escaped_thumbnail_filename, 'jpg')
        self.to_screen('Converting thumbnail "%s" to JPEG' % escaped_thumbnail_filename)
        self.run_ffmpeg(escaped_thumbnail_filename, escaped_thumbnail_jpg_filename, ['-bsf:v', 'mjpeg2jpeg'])
        thumbnail_jpg_filename = replace_extension(thumbnail_filename, 'jpg')
        # Rename back to unescaped
        os.rename(encodeFilename(escaped_thumbnail_filename), encodeFilename(thumbnail_filename))
        os.rename(encodeFilename(escaped_thumbnail_jpg_filename), encodeFilename(thumbnail_jpg_filename))
        return thumbnail_jpg_filename

    def run(self, info):
        if self.format != 'jpg':
            raise FFmpegPostProcessorError('Only conversion to jpg is currently supported')
        files_to_delete = []
        has_thumbnail = False

        for idx, thumbnail_dict in enumerate(info['thumbnails']):
            if 'filepath' not in thumbnail_dict:
                continue
            has_thumbnail = True
            self.fixup_webp(info, idx)
            original_thumbnail = thumbnail_dict['filepath']
            _, thumbnail_ext = os.path.splitext(original_thumbnail)
            if thumbnail_ext:
                thumbnail_ext = thumbnail_ext[1:].lower()
            if thumbnail_ext == self.format:
                self.to_screen('Thumbnail "%s" is already in the requested format' % original_thumbnail)
                continue
            thumbnail_dict['filepath'] = self.convert_thumbnail(original_thumbnail, self.format)
            files_to_delete.append(original_thumbnail)
            info['__files_to_move'][thumbnail_dict['filepath']] = replace_extension(
                info['__files_to_move'][original_thumbnail], self.format)

        if not has_thumbnail:
            self.to_screen('There aren\'t any thumbnails to convert')
        return files_to_delete, info
