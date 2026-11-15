#!/usr/bin/env python3
"""Dump every option the yt-dlp command line parser knows about to JSON.

The desktop app builds its Advanced screen, its command builder and
FEATURE_MATRIX.md from this file, so nothing the CLI accepts can be missed.

Usage: python3 desktop/scripts/gen_options.py [output.json]
"""
import json
import optparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from yt_dlp.options import create_parser  # noqa: E402
from yt_dlp.version import __version__  # noqa: E402


def jsonable(value):
    if value is optparse.NO_DEFAULT or value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return str(value)


def describe(option, group, parser):
    hidden = option.help == optparse.SUPPRESS_HELP
    default = parser.defaults.get(option.dest) if option.dest else None
    help_text = '' if hidden or not option.help else option.help
    if '%default' in help_text:
        help_text = help_text.replace('%default', str(default))
    callback = option.callback.__name__ if option.callback else None
    kwargs = option.callback_kwargs or {}
    const = option.const
    if callback == '_deprecated_option_callback':
        hidden = True
    return {
        'id': option.get_opt_string(),
        'flags': option._short_opts + option._long_opts,
        'group': group,
        'action': option.action,
        'type': option.type,
        'dest': option.dest,
        'default': jsonable(default),
        'const': jsonable(const),
        'choices': list(option.choices) if option.choices else None,
        'metavar': option.metavar,
        'help': ' '.join(help_text.split()),
        'hidden': hidden,
        'takesValue': option.takes_value(),
        'nargs': option.nargs or (1 if option.takes_value() else 0),
        'callback': callback,
        'allowedKeys': kwargs.get('allowed_keys'),
        'allowedValues': jsonable(kwargs.get('allowed_values')),
        'multipleKeys': kwargs.get('multiple_keys'),
    }


def main():
    parser = create_parser()
    options = [describe(o, 'General Options', parser) for o in parser.option_list
               if o.help != optparse.SUPPRESS_HELP]
    hidden_top = [describe(o, 'Deprecated', parser) for o in parser.option_list
                  if o.help == optparse.SUPPRESS_HELP]
    groups = []
    for group in parser.option_groups:
        groups.append({'title': group.title, 'description': group.description or ''})
        options.extend(describe(o, group.title, parser) for o in group.option_list)
    options.extend(hidden_top)
    out = {'engineVersion': __version__, 'groups': groups, 'options': options}
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, 'desktop', 'src', 'shared', 'options.generated.json')
    with open(target, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f'{len(options)} options written to {target}')


if __name__ == '__main__':
    main()
