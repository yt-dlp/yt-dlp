from __future__ import unicode_literals

import io
import itertools
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
    traverse_obj,
    variadic,
)



format2mux = {
    'mp4': 'mp4mux',
    'mkv': 'matroskamux',
}


class GstPostProcessorError(PostProcessingError):
    pass


class GstPostProcessor(PostProcessor):
    def __init__(self, downloader=None):
        PostProcessor.__init__(self, downloader)
        self._determine_executables()

    def check_version(self):
        if not self.available:
            raise GstPostProcessorError('gst-launch-1.0 not found. Please install or provide the path using --gst-location')

    @staticmethod
    def get_versions(downloader=None):
        return GstPostProcessor(downloader)._versions

    def _determine_executables(self):
        programs = ['ges-launch-1.0', 'gst-launch-1.0', 'gst-discoverer-1.0']
        def get_gstreamer_version(path):
            ver = get_exe_version(path, args=['--gst-version'])
            return ver

        self.basename = None
        self.probe_basename = None
        self.editor_basename = None
        self._paths = None
        self._versions = None
        if self._downloader:
            location = self.get_param('gst_location')
            if location is not None:
                if not os.path.exists(location):
                    self.report_warning(
                        'gstreamer-location %s does not exist! '
                        'Continuing without gstreamer.' % (location))
                    self._versions = {}
                    return
                elif os.path.isdir(location):
                    dirname, basename = location, None
                else:
                    basename = os.path.splitext(os.path.basename(location))[0]
                    basename = next((p for p in programs if basename.startswith(p)), 'gst-launch-1.0')
                    dirname = os.path.dirname(os.path.abspath(location))

                self._paths = dict(
                    (p, os.path.join(dirname, p)) for p in programs)
                if basename:
                    self._paths[basename] = location
                self._versions = dict(
                    (p, get_gstreamer_version(self._paths[p])) for p in programs)
        if self._versions is None:
            self._versions = dict(
                (p, get_gstreamer_version(p)) for p in programs)
            self._paths = dict((p, p) for p in programs)

        self.basename = "gst-launch-1.0"
        self.editor_basename = "ges-launch-1.0"
        self.probe_basename = "gst-discoverer-1.0"

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
        if not self.probe_available:
            raise PostProcessingError('gst-discoverer-1.0 is missing . Please install or provide the path using --gst-location')
        try:
            cmd = [encodeFilename(self.probe_executable, True)]
            cmd.append(encodeFilename(path, True))
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
        audio_codec = None
        for line in output.split('\n'):
            if line.startswith('    audio: '): # white space is important since gst indents response
                audio_codec = line.split(':')[1].strip()
                return audio_codec
        return None

class GstMergerPP(GstPostProcessor):
    @PostProcessor._restrict_to(images=False)
    def run(self, info):
        filename = info['filepath']
        temp_filename = prepend_extension(filename, 'temp')
        g = 0
        args = [encodeFilename(self.basename, True)]
        for i in info['__files_to_merge']:
            args = args + ['filesrc', 'location','=', encodeFilename(i), 'name=file'+str(g)]
            g = g + 1
        # add pipeline
        ext = filename.split('.')[-1]
        args = args + [format2mux[ext], "name=mux", "!", "filesink", "location","=",encodeFilename(temp_filename) + ""]
        g = 0
        for i in info['__files_to_merge']:
            args = args + ['file' + str(g) + ".", "!", 'parsebin', "!", "mux."]
            g = g + 1
        self.to_screen('Merging formats into "%s"' % filename)
        self.write_debug('gst command line: %s' % shell_quote(args))
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout, stderr = process_communicate_or_kill(p)
        if p.returncode not in variadic((0,)):
            stderr = stderr.decode('utf-8', 'replace').strip()
            if self.get_param('verbose', False):
                self.report_error(stderr)
            raise GstPostProcessorError(stderr.split('\n')[-1])
        os.rename(encodeFilename(temp_filename), encodeFilename(filename))
        return info['__files_to_merge'], info

    def can_merge(self):
        # TODO: figure out merge-capable gst version
        return True
