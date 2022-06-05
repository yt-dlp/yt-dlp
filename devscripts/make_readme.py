#!/usr/bin/env python3

# yt-dlp --help | make_readme.py
# This must be run in a console of correct width
import functools
import re
import sys

README_FILE = 'README.md'

OPTIONS_START = 'General Options:'
OPTIONS_END = 'CONFIGURATION'
EPILOG_START = 'See full documentation'

DISABLE_PATCH = object()


def take_section(text, start=None, end=None, *, shift=0):
    return text[
        text.index(start) + shift if start else None:
        text.index(end) + shift if end else None
    ]


def apply_patch(text, patch):
    return text if patch[0] is DISABLE_PATCH else re.sub(*patch, text)


options = take_section(sys.stdin.read(), f'\n  {OPTIONS_START}', f'\n{EPILOG_START}', shift=1)

switch_col_width = len(re.search(r'(?m)^\s{5,}', options).group())
delim = f'\n{" " * switch_col_width}'

PATCHES = (
    (  # Headings
        r'(?m)^  (\w.+\n)(    (?=\w))?',
        r'## \1'
    ),
    (  # Do not split URLs
        rf'({delim[:-1]})? (?P<label>\[\S+\] )?(?P<url>https?({delim})?:({delim})?/({delim})?/(({delim})?\S+)+)\s',
        lambda mobj: ''.join((delim, mobj.group('label') or '', re.sub(r'\s+', '', mobj.group('url')), '\n'))
    ),
    (  # Do not split "words"
        rf'(?m)({delim}\S+)+$',
        lambda mobj: ''.join((delim, mobj.group(0).replace(delim, '')))
    ),
    (  # Avoid newline when a space is available b/w switch and description
        DISABLE_PATCH,  # This creates issues with prepare_manpage
        r'(?m)^(\s{4}-.{%d})(%s)' % (switch_col_width - 6, delim),
        r'\1 '
    ),
)

with open(README_FILE, encoding='utf-8') as f:
    readme = f.read()

with open(README_FILE, 'w', encoding='utf-8') as f:
    f.write(''.join((
        take_section(readme, end=f'## {OPTIONS_START}'),
        functools.reduce(apply_patch, PATCHES, options),
        take_section(readme, f'# {OPTIONS_END}'),
    )))
