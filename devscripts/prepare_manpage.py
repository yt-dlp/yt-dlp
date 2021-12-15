#!/usr/bin/env python3
from __future__ import unicode_literals

import io
import optparse
import os.path
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_FILE = os.path.join(ROOT_DIR, 'README.md')

PREFIX = r'''%yt-dlp(1)

# NAME

yt\-dlp \- download videos from youtube.com or other video platforms

# SYNOPSIS

**yt-dlp** \[OPTIONS\] URL [URL...]

# DESCRIPTION

'''


def main():
    parser = optparse.OptionParser(usage='%prog OUTFILE.md')
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error('Expected an output filename')

    outfile, = args

    with io.open(README_FILE, encoding='utf-8') as f:
        readme = f.read()

    readme = re.sub(r'(?s)^.*?(?=# DESCRIPTION)', '', readme)
    readme = re.sub(r'\s+yt-dlp \[OPTIONS\] URL \[URL\.\.\.\]', '', readme)
    readme = filter_excluded_sections(readme)
    readme = move_section('usage and options', readme)
    readme = move_section('installation', readme)
    readme = re.sub(r'^# USAGE AND OPTIONS$', '# OPTIONS', readme, 1, flags=re.M)
    readme = PREFIX + readme

    readme = filter_options(readme)

    with io.open(outfile, 'w', encoding='utf-8') as outf:
        outf.write(readme)


def filter_excluded_sections(readme):
    EXCLUDED_SECTION_BEGIN_STRING = '<!-- MANPAGE: BEGIN EXCLUDED SECTION -->'
    EXCLUDED_SECTION_END_STRING = '<!-- MANPAGE: END EXCLUDED SECTION -->'
    return re.sub(
        rf'(?s){re.escape(EXCLUDED_SECTION_BEGIN_STRING)}.+?{re.escape(EXCLUDED_SECTION_END_STRING)}\n',
        '', readme)


def move_section(section_name, readme):
    section_name = section_name.upper()
    move_tag = '<!-- MANPAGE: MOVE \"%s\" SECTION HERE -->' % section_name
    section_pattern = '(?sm)(^# %s.+?)^# ' % section_name
    section = re.findall(section_pattern, readme)
    if len(section) < 1:
        raise Exception("The section %s does not exist" % section_name)
    elif len(section) > 1:
        raise Exception("There are multiple occurrences of section %s, this is unhandled" % section_name)
    else:
        pass
    readme_without_section = re.sub(section_pattern, '# ', readme, 1)
    if readme_without_section.count(move_tag) < 1:
        raise Exception('Moving the "%s" section was requested, but no "%s" marker was found.' % (section_name, move_tag))
    elif readme_without_section.count(move_tag) > 1:
        raise Warning('There is more than one occurrence of "%s". This is probably an accident.' % move_tag)
    return readme_without_section.replace(move_tag, section[0])


def filter_options(readme):
    ret = ''
    in_options = False
    for line in readme.split('\n'):
        if line.startswith('# '):
            if line[2:].startswith('OPTIONS'):
                in_options = True
            else:
                in_options = False

        if in_options:
            if line.lstrip().startswith('-'):
                split = re.split(r'\s{2,}', line.lstrip())
                # Description string may start with `-` as well. If there is
                # only one piece then it's a description bit not an option.
                if len(split) > 1:
                    option, description = split
                    split_option = option.split(' ')

                    if not split_option[-1].startswith('-'):  # metavar
                        option = ' '.join(split_option[:-1] + ['*%s*' % split_option[-1]])

                    # Pandoc's definition_lists. See http://pandoc.org/README.html
                    # for more information.
                    ret += '\n%s\n:   %s\n' % (option, description)
                    continue
            ret += line.lstrip() + '\n'
        else:
            ret += line + '\n'

    return ret


if __name__ == '__main__':
    main()
