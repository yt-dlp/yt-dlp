#!/usr/bin/env python
from __future__ import unicode_literals

# import io
import optparse
# import re


def main():
    parser = optparse.OptionParser(usage='%prog INFILE OUTFILE')
    options, args = parser.parse_args()
    if len(args) != 2:
        parser.error('Expected an input and an output filename')


"""     infile, outfile = args

    with io.open(infile, encoding='utf-8') as inf:
        readme = inf.read()

    bug_text = re.search( """
# r'(?s)#\s*BUGS\s*[^\n]*\s*(.*?)#\s*COPYRIGHT', readme).group(1)
# dev_text = re.search(
# r'(?s)(#\s*DEVELOPER INSTRUCTIONS.*?)#\s*EMBEDDING yt-dlp',
"""         readme).group(1)

    out = bug_text + dev_text

    with io.open(outfile, 'w', encoding='utf-8') as outf:
        outf.write(out) """

if __name__ == '__main__':
    main()
