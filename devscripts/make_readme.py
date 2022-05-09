#!/usr/bin/env python3

# yt-dlp --help | make_readme.py
# This must be run in a console of correct width
import re
import sys

README_FILE = 'README.md'

OPTIONS_START = 'General Options:'
OPTIONS_END = 'CONFIGURATION'
EPILOG_START = 'See full documentation'


helptext = sys.stdin.read()
if isinstance(helptext, bytes):
    helptext = helptext.decode()

start, end = helptext.index(f'\n  {OPTIONS_START}'), helptext.index(f'\n{EPILOG_START}')
options = re.sub(r'(?m)^  (\w.+)$', r'## \1', helptext[start + 1: end + 1])

with open(README_FILE, encoding='utf-8') as f:
    readme = f.read()

header = readme[:readme.index(f'## {OPTIONS_START}')]
footer = readme[readme.index(f'# {OPTIONS_END}'):]

with open(README_FILE, 'w', encoding='utf-8') as f:
    for part in (header, options, footer):
        f.write(part)
