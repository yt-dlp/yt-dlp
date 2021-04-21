from __future__ import unicode_literals

import re

from .common import PostProcessor
from ..compat import compat_str


class MetadataFromFieldPP(PostProcessor):
    regex = r'(?P<in>.*?)(?<!\\):(?P<out>.+)$'

    def __init__(self, downloader, formats):
        PostProcessor.__init__(self, downloader)
        assert isinstance(formats, (list, tuple))
        self._data = []
        for f in formats:
            assert isinstance(f, compat_str)
            match = re.match(self.regex, f)
            assert match is not None
            inp = match.group('in').replace('\\:', ':')
            self._data.append({
                'in': inp,
                'out': match.group('out'),
                'tmpl': self.field_to_template(inp),
                'regex': self.format_to_regex(match.group('out')),
            })

    @staticmethod
    def field_to_template(tmpl):
        if re.match(r'\w+$', tmpl):
            return '%%(%s)s' % tmpl
        return tmpl

    @staticmethod
    def format_to_regex(fmt):
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
            regex += r'(?P<%s>.+)' % match.group(1)
            lastpos = match.end()
        if lastpos < len(fmt):
            regex += re.escape(fmt[lastpos:])
        return regex

    def run(self, info):
        for dictn in self._data:
            tmpl, info_copy = self._downloader.prepare_outtmpl(dictn['tmpl'], info)
            data_to_parse = tmpl % info_copy
            self.write_debug('Searching for r"%s" in %s' % (dictn['regex'], tmpl))
            match = re.search(dictn['regex'], data_to_parse)
            if match is None:
                self.report_warning('Could not interpret video %s as "%s"' % (dictn['in'], dictn['out']))
                continue
            for attribute, value in match.groupdict().items():
                info[attribute] = value
                self.to_screen('parsed %s from "%s": %s' % (attribute, dictn['in'], value if value is not None else 'NA'))
        return [], info


class MetadataFromTitlePP(MetadataFromFieldPP):  # for backward compatibility
    def __init__(self, downloader, titleformat):
        super(MetadataFromTitlePP, self).__init__(downloader, ['%%(title)s:%s' % titleformat])
        self._titleformat = titleformat
        self._titleregex = self._data[0]['regex']
