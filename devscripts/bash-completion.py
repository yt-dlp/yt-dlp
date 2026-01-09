#!/usr/bin/env python3

# Allow direct execution
import os
import shlex
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import yt_dlp

BASH_COMPLETION_FILE = 'completions/bash/yt-dlp'
BASH_COMPLETION_TEMPLATE = 'devscripts/bash-completion.in'


@dataclass
class YtDlpOpts:
    opts: tuple[str, ...]
    file_opts: tuple[str, ...]
    dir_opts: tuple[str, ...]


def yt_dlp_options():
    opts, long_opts = [], []
    file_opts, dir_opts = [], []

    for opt in yt_dlp.parseOpts(ignore_config_files=True)[0]._get_all_options():
        opts.extend(opt._short_opts)
        long_opts.extend(opt._long_opts)
        if opt.metavar in {'FILE', 'PATH', 'CERTFILE', 'KEYFILE'}:
            file_opts.extend(opt._short_opts)
            file_opts.extend(opt._long_opts)
        elif opt.metavar == 'DIR':
            dir_opts.extend(opt._short_opts)
            dir_opts.extend(opt._long_opts)

    opts.sort()
    long_opts.sort()
    opts.extend(long_opts)

    return YtDlpOpts(tuple(opts), tuple(file_opts), tuple(dir_opts))


def build_completion():
    with open(BASH_COMPLETION_TEMPLATE) as f:
        template = f.read()
    with open(BASH_COMPLETION_FILE, 'w') as f:
        # just using the special char
        opts = yt_dlp_options()
        f.write(template.replace(
            'YT_DLP_FILE_OPTS_CASE', ' | '.join(shlex.quote(o) for o in opts.file_opts),
        ).replace(
            'YT_DLP_DIR_OPTS_CASE', ' | '.join(shlex.quote(o) for o in opts.dir_opts),
        ).replace(
            'YT_DLP_OPTS_ARRAY', ' '.join(shlex.quote(o) for o in opts.opts),
        ))


build_completion()
