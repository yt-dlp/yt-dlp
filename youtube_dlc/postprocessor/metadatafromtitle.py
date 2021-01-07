from __future__ import unicode_literals

import re

from .common import PostProcessor


class MetadataFromTitlePP(PostProcessor):
    def __init__(self, downloader, titleformat):
        super(MetadataFromTitlePP, self).__init__(downloader)
        self._titleformat = titleformat
        self._titleregex = (self.format_to_regex(titleformat)
                            if re.search(r'%\(\w+\)s', titleformat)
                            else titleformat)

    def format_to_regex(self, fmt):
        r"""
        Converts a string like
           '%(title)s - %(artist)s'
        to a regex like
           '(?P<title>.+)\ \-\ (?P<artist>.+)'
        """
        lastpos = 0
        regex = ''
        # replace %(..)s with regex group and escape other string parts
        for match in re.finditer(r'%\((\w+)\)s', fmt):
            regex += re.escape(fmt[lastpos:match.start()])
            regex += r'(?P<' + match.group(1) + '>.+)'
            lastpos = match.end()
        if lastpos < len(fmt):
            regex += re.escape(fmt[lastpos:])
        return regex

    def run(self, info):
        title = info['title']
        match = re.match(self._titleregex, title)
        if match is None:
            self.to_screen('Could not interpret title of video as "%s"' % self._titleformat)
            return [], info
        for attribute, value in match.groupdict().items():
            info[attribute] = value
            self.to_screen('parsed %s: %s' % (attribute, value if value is not None else 'NA'))

        return [], info
