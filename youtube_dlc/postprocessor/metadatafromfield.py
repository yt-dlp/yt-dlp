from __future__ import unicode_literals

import re

from .common import PostProcessor
from ..compat import compat_str
from ..utils import str_or_none


class MetadataFromFieldPP(PostProcessor):
    regex = r'(?P<field>\w+):(?P<format>.+)$'

    def __init__(self, downloader, formats):
        PostProcessor.__init__(self, downloader)
        assert isinstance(formats, (list, tuple))
        self._data = []
        for f in formats:
            assert isinstance(f, compat_str)
            match = re.match(self.regex, f)
            assert match is not None
            self._data.append({
                'field': match.group('field'),
                'format': match.group('format'),
                'regex': self.format_to_regex(match.group('format'))})

    def format_to_regex(self, fmt):
        r"""
        Converts a string like
           '%(title)s - %(artist)s'
        to a regex like
           '(?P<title>.+)\ \-\ (?P<artist>.+)'
        """
        if not re.search(r'%\(\w+\)s', fmt):
            return fmt
        lastpos = 0
        regex = ''
        # replace %(..)s with regex group and escape other string parts
        for match in re.finditer(r'%\((\w+)\)s', fmt):
            regex += re.escape(fmt[lastpos:match.start()])
            regex += r'(?P<' + match.group(1) + r'>[^\r\n]+)'
            lastpos = match.end()
        if lastpos < len(fmt):
            regex += re.escape(fmt[lastpos:])
        return regex

    def run(self, info):
        for dictn in self._data:
            field, regex = dictn['field'], dictn['regex']
            if field not in info:
                self.report_warning('Video doesnot have a %s' % field)
                continue
            data_to_parse = str_or_none(info[field])
            if data_to_parse is None:
                self.report_warning('Field %s cannot be parsed' % field)
                continue
            self.write_debug('Searching for r"%s" in %s' % (regex, field))
            match = re.search(regex, data_to_parse)
            if match is None:
                self.report_warning('Could not interpret video %s as "%s"' % (field, dictn['format']))
                continue
            for attribute, value in match.groupdict().items():
                info[attribute] = value
                self.to_screen('parsed %s from %s: %s' % (attribute, field, value if value is not None else 'NA'))
        return [], info


class MetadataFromTitlePP(MetadataFromFieldPP):  # for backward compatibility
    def __init__(self, downloader, titleformat):
        super(MetadataFromTitlePP, self).__init__(downloader, ['title:%s' % titleformat])
        self._titleformat = titleformat
        self._titleregex = self._data[0]['regex']
