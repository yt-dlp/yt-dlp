#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import yt_dlp
from devscripts.utils import gather_completion_opts

BASH_COMPLETION_FILE = 'completions/bash/yt-dlp'
BASH_COMPLETION_TEMPLATE = 'devscripts/bash-completion.in'


def build_completion(opt_parser):
    opts = gather_completion_opts(opt_parser)

    with open(BASH_COMPLETION_TEMPLATE) as f:
        template = f.read()

    template = template.replace('YT_DLP_FILE_OPTS_CASE', ' | '.join(opts.file_opts))
    template = template.replace('YT_DLP_DIR_OPTS_CASE', ' | '.join(opts.dir_opts))
    template = template.replace('YT_DLP_OPTS_ARRAY', ' '.join(opts.opts))

    with open(BASH_COMPLETION_FILE, 'w') as f:
        f.write(template)


parser = yt_dlp.parseOpts(ignore_config_files=True)[0]
build_completion(parser)
