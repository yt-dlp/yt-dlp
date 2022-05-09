#!/usr/bin/env python3
import optparse
import os.path
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_FILE = os.path.join(ROOT_DIR, 'README.md')

PREFIX = r'''%yt-dlp(1)

# NAME

yt\-dlp \- A youtube-dl fork with additional features and patches

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

    with open(README_FILE, encoding='utf-8') as f:
        readme = f.read()

    readme = filter_excluded_sections(readme)
    readme = move_sections(readme)
    readme = filter_options(readme)

    with open(outfile, 'w', encoding='utf-8') as outf:
        outf.write(PREFIX + readme)


def filter_excluded_sections(readme):
    EXCLUDED_SECTION_BEGIN_STRING = re.escape('<!-- MANPAGE: BEGIN EXCLUDED SECTION -->')
    EXCLUDED_SECTION_END_STRING = re.escape('<!-- MANPAGE: END EXCLUDED SECTION -->')
    return re.sub(
        rf'(?s){EXCLUDED_SECTION_BEGIN_STRING}.+?{EXCLUDED_SECTION_END_STRING}\n',
        '', readme)


def move_sections(readme):
    MOVE_TAG_TEMPLATE = '<!-- MANPAGE: MOVE "%s" SECTION HERE -->'
    sections = re.findall(r'(?m)^%s$' % (
        re.escape(MOVE_TAG_TEMPLATE).replace(r'\%', '%') % '(.+)'), readme)

    for section_name in sections:
        move_tag = MOVE_TAG_TEMPLATE % section_name
        if readme.count(move_tag) > 1:
            raise Exception(f'There is more than one occurrence of "{move_tag}". This is unexpected')

        sections = re.findall(rf'(?sm)(^# {re.escape(section_name)}.+?)(?=^# )', readme)
        if len(sections) < 1:
            raise Exception(f'The section {section_name} does not exist')
        elif len(sections) > 1:
            raise Exception(f'There are multiple occurrences of section {section_name}, this is unhandled')

        readme = readme.replace(sections[0], '', 1).replace(move_tag, sections[0], 1)
    return readme


def filter_options(readme):
    section = re.search(r'(?sm)^# USAGE AND OPTIONS\n.+?(?=^# )', readme).group(0)
    options = '# OPTIONS\n'
    for line in section.split('\n')[1:]:
        mobj = re.fullmatch(r'''(?x)
                \s{4}(?P<opt>-(?:,\s|[^\s])+)
                (?:\s(?P<meta>(?:[^\s]|\s(?!\s))+))?
                (\s{2,}(?P<desc>.+))?
            ''', line)
        if not mobj:
            options += f'{line.lstrip()}\n'
            continue
        option, metavar, description = mobj.group('opt', 'meta', 'desc')

        # Pandoc's definition_lists. See http://pandoc.org/README.html
        option = f'{option} *{metavar}*' if metavar else option
        description = f'{description}\n' if description else ''
        options += f'\n{option}\n:   {description}'
        continue

    return readme.replace(section, options, 1)


if __name__ == '__main__':
    main()
