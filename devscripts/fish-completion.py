#!/usr/bin/env python
from __future__ import unicode_literals

import optparse
import os
from os.path import dirname as dirn
import sys

sys.path.insert(0, dirn(dirn((os.path.abspath(__file__)))))
import yt_dlp
from yt_dlp.utils import shell_quote

FISH_COMPLETION_FILE = 'completions/fish/yt-dlp.fish'
FISH_COMPLETION_TEMPLATE = 'devscripts/fish-completion.in'

EXTRA_ARGS = {
    'remux-video': ['--arguments', 'mp4 mkv', '--exclusive'],
    'recode-video': ['--arguments', 'mp4 flv ogg webm mkv', '--exclusive'],

    # Options that need a file parameter
    'download-archive': ['--require-parameter'],
    'cookies': ['--require-parameter'],
    'load-info': ['--require-parameter'],
    'batch-file': ['--require-parameter'],
}


def build_completion(opt_parser):
    commands = []

    for group in opt_parser.option_groups:
        for option in group.option_list:
            long_option = option.get_opt_string().strip('-')
            complete_cmd = ['complete', '--command', 'yt-dlp', '--long-option', long_option]
            if option._short_opts:
                complete_cmd += ['--short-option', option._short_opts[0].strip('-')]
            if option.help != optparse.SUPPRESS_HELP:
                complete_cmd += ['--description', option.help]
            complete_cmd.extend(EXTRA_ARGS.get(long_option, []))
            commands.append(shell_quote(complete_cmd))

    with open(FISH_COMPLETION_TEMPLATE) as f:
        template = f.read()
    filled_template = template.replace('{{commands}}', '\n'.join(commands))
    with open(FISH_COMPLETION_FILE, 'w') as f:
        f.write(filled_template)


parser = yt_dlp.parseOpts()[0]
build_completion(parser)
