#!/usr/bin/env python3
import optparse


def read(fname):
    with open(fname, encoding='utf-8') as f:
        return f.read()


# Get the version from yt_dlp/version.py without importing the package
def read_version(fname):
    exec(compile(read(fname), fname, 'exec'))
    return locals()['__version__']


def main():
    parser = optparse.OptionParser(usage='%prog INFILE OUTFILE')
    options, args = parser.parse_args()
    if len(args) != 2:
        parser.error('Expected an input and an output filename')

    infile, outfile = args
    with open(outfile, 'w', encoding='utf-8') as outf:
        outf.write(
            read(infile) % {'version': read_version('yt_dlp/version.py')})


if __name__ == '__main__':
    main()
