#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from devscripts.utils import get_filename_args, write_file
from yt_dlp.extractor import list_extractor_classes

TEMPLATE = '''\
# Supported sites

Below is a list of all extractors that are currently included with yt-dlp.
If a site is not listed here, it might still be supported by yt-dlp's embed extraction or generic extractor.
Not all sites listed here are guaranteed to work; websites are constantly changing and sometimes this breaks yt-dlp's support for them.
The only reliable way to check if a site is supported is to try it.

{ie_list}
'''


def main():
    out = '\n'.join(ie.description() for ie in list_extractor_classes() if ie.IE_DESC is not False)
    write_file(get_filename_args(), TEMPLATE.format(ie_list=out))


if __name__ == '__main__':
    main()
