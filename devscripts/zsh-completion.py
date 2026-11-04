#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import yt_dlp
from devscripts.utils import gather_completion_opts

ZSH_COMPLETION_FILE = 'completions/zsh/_yt-dlp'
ZSH_COMPLETION_TEMPLATE = 'devscripts/zsh-completion.in'


def build_completion(opt_parser):
    opts = gather_completion_opts(opt_parser)

    with open(ZSH_COMPLETION_TEMPLATE) as f:
        template = f.read()

    template = template.replace('{{fileopts}}', '|'.join(opts.file_opts))
    template = template.replace('{{diropts}}', '|'.join(opts.dir_opts))
    template = template.replace('{{flags}}', ' '.join(opts.opts))

    with open(ZSH_COMPLETION_FILE, 'w') as f:
        f.write(template)


parser = yt_dlp.parseOpts(ignore_config_files=True)[0]
build_completion(parser)
