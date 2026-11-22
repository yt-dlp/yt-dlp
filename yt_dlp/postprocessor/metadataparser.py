import re

from .common import PostProcessor
from ..utils import Namespace, filter_dict, function_with_repr


class MetadataParserPP(PostProcessor):
    def __init__(self, downloader, actions):
        super().__init__(downloader)
        self._actions = []
        for f in actions:
            action, *args = f
            assert action in self.Actions
            self._actions.append(action(self, *args))

    @classmethod
    def validate_action(cls, action, *data):
        """Each action can be:
                (Actions.INTERPRET, from, to) OR
                (Actions.REPLACE, field, search, replace)
        """
        if action not in cls.Actions:
            raise ValueError(f'{action!r} is not a valid action')
        action(cls, *data)  # So this can raise error to validate

    @staticmethod
    def field_to_template(tmpl):
        if re.match(r'[a-zA-Z_]+$', tmpl):
            return f'%({tmpl})s'

        from ..YoutubeDL import YoutubeDL
        err = YoutubeDL.validate_outtmpl(tmpl)
        if err:
            raise err
        return tmpl

    @staticmethod
    def format_to_regex(fmt):
        r"""
        Converts a string like
           '%(title)s - %(artist)s'
        to a regex like
           '(?P<title>.+)\ \-\ (?P<artist>.+)'
        """
        if re.fullmatch(r'\w+', fmt):
            # convert a single field name into regex pattern that matches the entire input
            return rf'(?s)(?P<{fmt}>.+)'
        if not re.search(r'%\(\w+\)s', fmt):
            return fmt
        lastpos = 0
        regex = ''
        # replace %(..)s with regex group and escape other string parts
        for match in re.finditer(r'%\((\w+)\)s', fmt):
            regex += re.escape(fmt[lastpos:match.start()])
            regex += rf'(?P<{match.group(1)}>.+)'
            lastpos = match.end()
        if lastpos < len(fmt):
            regex += re.escape(fmt[lastpos:])
        return regex

    def run(self, info):
        for f in self._actions:
            f(info)
        return [], info

    @function_with_repr
    def interpretter(self, inp, out):
        def f(info):
            data_to_parse = self._downloader.evaluate_outtmpl(template, info)
            self.write_debug(f'Searching for {out_re.pattern!r} in {template!r}')
            match = out_re.search(data_to_parse)
            if match is None:
                self.to_screen(f'Could not interpret {inp!r} as {out!r}')
                return
            for attribute, value in filter_dict(match.groupdict()).items():
                info[attribute] = value
                self.to_screen(f'Parsed {attribute} from {template!r}: {value!r}')

        template = self.field_to_template(inp)
        out_re = re.compile(self.format_to_regex(out))
        return f

    @function_with_repr
    def replacer(self, field, search, replace):
        def f(info):
            val = info.get(field)
            if val is None:
                self.to_screen(f'Video does not have a {field}')
                return
            elif not isinstance(val, str):
                self.report_warning(f'Cannot replace in field {field} since it is a {type(val).__name__}')
                return
            self.write_debug(f'Replacing all {search!r} in {field} with {replace!r}')
            info[field], n = search_re.subn(replace, val)
            if n:
                self.to_screen(f'Changed {field} to: {info[field]}')
            else:
                self.to_screen(f'Did not find {search!r} in {field}')

        search_re = re.compile(search)
        return f

    Actions = Namespace(INTERPRET=interpretter, REPLACE=replacer)


class MetadataFromFieldPP(MetadataParserPP):
    @classmethod
    def to_action(cls, f):
        match = re.match(r'(?s)(?P<in>.*?)(?<!\\):(?P<out>.+)$', f)
        if match is None:
            raise ValueError(f'it should be FROM:TO, not {f!r}')
        return (
            cls.Actions.INTERPRET,
            match.group('in').replace('\\:', ':'),
            match.group('out'),
        )

    def __init__(self, downloader, formats):
        super().__init__(downloader, [self.to_action(f) for f in formats])


# Deprecated
class MetadataFromTitlePP(MetadataParserPP):
    def __init__(self, downloader, titleformat):
        super().__init__(downloader, [(self.Actions.INTERPRET, 'title', titleformat)])
        self.deprecation_warning(
            'yt_dlp.postprocessor.MetadataFromTitlePP is deprecated '
            'and may be removed in a future version. Use yt_dlp.postprocessor.MetadataFromFieldPP instead')
