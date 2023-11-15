#!/usr/bin/env python3

"""
yt-dlp --help | make_readme.py
This must be run in a console of correct width
"""

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import functools
import re

from devscripts.utils import read_file, write_file

README_FILE = 'README.md'

OPTIONS_START = 'General Options:'
OPTIONS_END = 'CONFIGURATION'
EPILOG_START = 'See full documentation'
ALLOWED_OVERSHOOT = 2

DISABLE_PATCH = object()


def take_section(text, start=None, end=None, *, shift=0):
    return text[
        text.index(start) + shift if start else None:
        text.index(end) + shift if end else None
    ]


def apply_patch(text, patch):
    return text if patch[0] is DISABLE_PATCH else re.sub(*patch, text)


options = take_section(sys.stdin.read(), f'\n  {OPTIONS_START}', f'\n{EPILOG_START}', shift=1)

max_width = max(map(len, options.split('\n')))
switch_col_width = len(re.search(r'(?m)^\s{5,}', options).group())
delim = f'\n{" " * switch_col_width}'

PATCHES = (
    (   # Standardize `--update` message
        r'(?m)^(    -U, --update\s+).+(\n    \s.+)*$',
        r'\1Update this program to the latest version',
    ),
    (   # Headings
        r'(?m)^  (\w.+\n)(    (?=\w))?',
        r'## \1'
    ),
    (   # Fixup `--date` formatting
        rf'(?m)(    --date DATE.+({delim}[^\[]+)*)\[.+({delim}.+)*$',
        (rf'\1[now|today|yesterday][-N[day|week|month|year]].{delim}'
         f'E.g. "--date today-2weeks" downloads only{delim}'
         'videos uploaded on the same day two weeks ago'),
    ),
    (   # Do not split URLs
        rf'({delim[:-1]})? (?P<label>\[\S+\] )?(?P<url>https?({delim})?:({delim})?/({delim})?/(({delim})?\S+)+)\s',
        lambda mobj: ''.join((delim, mobj.group('label') or '', re.sub(r'\s+', '', mobj.group('url')), '\n'))
    ),
    (   # Do not split "words"
        rf'(?m)({delim}\S+)+$',
        lambda mobj: ''.join((delim, mobj.group(0).replace(delim, '')))
    ),
    (   # Allow overshooting last line
        rf'(?m)^(?P<prev>.+)${delim}(?P<current>.+)$(?!{delim})',
        lambda mobj: (mobj.group().replace(delim, ' ')
                      if len(mobj.group()) - len(delim) + 1 <= max_width + ALLOWED_OVERSHOOT
                      else mobj.group())
    ),
    (   # Avoid newline when a space is available b/w switch and description
        DISABLE_PATCH,  # This creates issues with prepare_manpage
        r'(?m)^(\s{4}-.{%d})(%s)' % (switch_col_width - 6, delim),
        r'\1 '
    ),
    (   # Replace brackets with a Markdown link
        r'SponsorBlock API \((http.+)\)',
        r'[SponsorBlock API](\1)'
    ),
)

readme = read_file(README_FILE)

write_file(README_FILE, ''.join((
    take_section(readme, end=f'## {OPTIONS_START}'),
    functools.reduce(apply_patch, PATCHES, options),
    take_section(readme, f'# {OPTIONS_END}'),
)))
