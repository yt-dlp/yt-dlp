#!/usr/bin/env python3
import optparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.extractor import list_extractor_classes


def main():
    parser = optparse.OptionParser(usage='%prog OUTFILE.md')
    _, args = parser.parse_args()
    if len(args) != 1:
        parser.error('Expected an output filename')

    out = '\n'.join(ie.description() for ie in list_extractor_classes() if ie.IE_DESC is not False)

    with open(args[0], 'w', encoding='utf-8') as outf:
        outf.write(f'# Supported sites\n{out}\n')


if __name__ == '__main__':
    main()
