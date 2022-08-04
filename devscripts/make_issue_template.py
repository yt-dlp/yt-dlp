#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import optparse
import re


def read(fname):
    with open(fname, encoding='utf-8') as f:
        return f.read()


# Get the version without importing the package
def read_version(fname):
    exec(compile(read(fname), fname, 'exec'))
    return locals()['__version__']


VERBOSE_TMPL = '''
  - type: checkboxes
    id: verbose
    attributes:
      label: Provide verbose output that clearly demonstrates the problem
      options:
        - label: Run **your** yt-dlp command with **-vU** flag added (`yt-dlp -vU <your command line>`)
          required: true
        - label: Copy the WHOLE output (starting with `[debug] Command-line config`) and insert it below
          required: true
  - type: textarea
    id: log
    attributes:
      label: Complete Verbose Output
      description: |
        It should start like this:
      placeholder: |
        [debug] Command-line config: ['-vU', 'test:youtube']
        [debug] Portable config "yt-dlp.conf": ['-i']
        [debug] Encodings: locale cp65001, fs utf-8, pref cp65001, out utf-8, error utf-8, screen utf-8
        [debug] yt-dlp version %(version)s [9d339c4] (win32_exe)
        [debug] Python 3.8.10 (CPython 64bit) - Windows-10-10.0.22000-SP0
        [debug] Checking exe version: ffmpeg -bsfs
        [debug] Checking exe version: ffprobe -bsfs
        [debug] exe versions: ffmpeg N-106550-g072101bd52-20220410 (fdk,setts), ffprobe N-106624-g391ce570c8-20220415, phantomjs 2.1.1
        [debug] Optional libraries: Cryptodome-3.15.0, brotli-1.0.9, certifi-2022.06.15, mutagen-1.45.1, sqlite3-2.6.0, websockets-10.3
        [debug] Proxy map: {}
        [debug] Fetching release info: https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest
        Latest version: %(version)s, Current version: %(version)s
        yt-dlp is up to date (%(version)s)
        <more lines>
      render: shell
    validations:
      required: true
'''.strip()


def main():
    parser = optparse.OptionParser(usage='%prog INFILE OUTFILE')
    _, args = parser.parse_args()
    if len(args) != 2:
        parser.error('Expected an input and an output filename')

    fields = {'version': read_version('yt_dlp/version.py')}
    fields['verbose'] = VERBOSE_TMPL % fields
    fields['verbose_optional'] = re.sub(r'(\n\s+validations:)?\n\s+required: true', '', fields['verbose'])

    infile, outfile = args
    with open(outfile, 'w', encoding='utf-8') as outf:
        outf.write(read(infile) % fields)


if __name__ == '__main__':
    main()
