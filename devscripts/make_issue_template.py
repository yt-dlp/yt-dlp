#!/usr/bin/env python
from __future__ import unicode_literals

import io
import optparse


def main():
    parser = optparse.OptionParser(usage='%prog INFILE OUTFILE')
    options, args = parser.parse_args()
    if len(args) != 2:
        parser.error('Expected an input and an output filename')

    infile, outfile = args

    with io.open(infile, encoding='utf-8') as inf:
        issue_template_tmpl = inf.read()

    # Get the version from yt_dlp/version.py without importing the package
    exec(compile(open('yt_dlp/version.py').read(),
                 'yt_dlp/version.py', 'exec'))

    out = issue_template_tmpl % {'version': locals()['__version__']}

    with io.open(outfile, 'w', encoding='utf-8') as outf:
        outf.write(out)

if __name__ == '__main__':
    main()
