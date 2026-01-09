#!/usr/bin/env python3

# Allow direct execution
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import yt_dlp

BASH_COMPLETION_FILE = 'completions/bash/yt-dlp'
BASH_COMPLETION_TEMPLATE = 'devscripts/bash-completion.in'


def yt_dlp_options():
    opts, long_opts = [], []

    for opt in yt_dlp.parseOpts(ignore_config_files=True)[0]._get_all_options():
        opts.extend(opt._short_opts)
        long_opts.extend(opt._long_opts)

    opts.sort()
    long_opts.sort()
    opts.extend(long_opts)

    for o in opts:
        yield shlex.quote(o)


def build_completion():
    with open(BASH_COMPLETION_TEMPLATE) as f:
        template = f.read()
    with open(BASH_COMPLETION_FILE, 'w') as f:
        # just using the special char
        filled_template = template.replace('YT_DLP_OPTS', ' '.join(yt_dlp_options()))
        f.write(filled_template)


build_completion()
