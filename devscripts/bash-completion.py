#!/usr/bin/env python3

# Allow direct execution
import os
import shlex
import sys
from itertools import chain

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import yt_dlp

BASH_COMPLETION_FILE = 'completions/bash/yt-dlp'
BASH_COMPLETION_TEMPLATE = 'devscripts/bash-completion.in'


def yt_dlp_flags():
    for opt in yt_dlp.parseOpts(ignore_config_files=True)[0]._get_all_options():
        for opt_str in chain(opt._short_opts, opt._long_opts):
            yield shlex.quote(opt_str)


def build_completion():
    with open(BASH_COMPLETION_TEMPLATE) as f:
        template = f.read()
    with open(BASH_COMPLETION_FILE, 'w') as f:
        # just using the special char
        filled_template = template.replace('YT_DLP_FLAGS', ' '.join(sorted(yt_dlp_flags())))
        f.write(filled_template)


build_completion()
