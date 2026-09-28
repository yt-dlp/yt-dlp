import collections
import contextlib
import itertools
import re
from html.parser import HTMLParser

from .compat import compat_HTMLParseError
from .utils import orderedSet


class HTMLIgnoreRanges:
    """check if an offset is within CDATA content elements (script, style) or XML comments

        note:
            * given offsets must be in increasing order
            * no detection of nested constructs (e.g. comments within script tags)

        usage:
            ranges = HTMLIgnoreRanges(html)
            if offset in ranges:
                ...
    """
    REGEX = re.compile(r'<!--|--!?>|</?\s*(?:script|style)\b[^>]*>', flags=re.IGNORECASE)

    def __init__(self, html):
        self.html = html
        self._last_match = None
        self._final = False

    def __contains__(self, offset):
        assert isinstance(offset, int)

        if not self._final and (self._last_match is None or offset >= self._last_match.end()):
            match = self.REGEX.search(self.html, offset)
            if match:
                self._last_match = match
            else:
                self._final = True

        if self._last_match is None:
            return False
        match_string = self._last_match.group()
        if match_string.startswith('</') or match_string in ('-->', '--!>'):
            return offset < self._last_match.start()
        return offset >= self._last_match.end()


class HTMLTagParser(HTMLParser):
    """HTML parser which returns found elements as instances of 'Tag'
    when STRICT=True can raise compat_HTMLParseError() on malformed HTML elements

    usage:
        parser = HTMLTagParser()
        for tag_obj in parser.taglist(html):
            tag_obj.text_and_html()

    """

    STRICT = False
    ANY_TAG_REGEX = re.compile(r'''<(?:"[^"]*"|'[^']*'|[^"'>])*?>''')
    VOID_TAGS = {
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'keygen', 'link', 'meta', 'param', 'source', 'track', 'wbr',
    }

    class Tag:
        __slots__ = 'name', 'string', 'attrs', '_openrange', '_closerange'

        def __init__(self, name, *, string='', attrs=()):
            self.name = name
            self.string = string
            self.attrs = tuple(attrs)
            self._openrange = None
            self._closerange = None

        def __str__(self):
            return self.name

        def __repr__(self):
            return f'{self.__class__.__name__}({str(self)!r})'

        def __eq__(self, other):
            return self.name == other

        def openrange(self, offset, startlen=0):
            if isinstance(offset, slice):
                self._openrange = offset
            else:
                self._openrange = slice(offset, offset + startlen)

        def closerange(self, offset, stoplen=0):
            if isinstance(offset, slice):
                self._closerange = offset
            else:
                self._closerange = slice(offset, offset + stoplen)

        def opentag(self):
            return self.string[self._openrange] if self._openrange else ''

        def html(self):
            if not self._openrange:
                return ''
            if self._closerange:
                return self.string[self._openrange.start:self._closerange.stop]
            return self.string[self._openrange]

        def text(self):
            if self._openrange and self._closerange:
                return self.string[self._openrange.stop:self._closerange.start]
            return ''

        def text_and_html(self):
            return self.text(), self.html()

    class AbortException(Exception):
        pass

    def __init__(self):
        self.tagstack = collections.deque()
        self._nestedtags = [[]]
        super().__init__()
        self._offset = self.offset

    def predicate(self, tag, attrs):
        """ return True for every encountered opening tag that should be processed """
        return True

    def callback(self, tag_obj):
        """ this will be called when the requested tag is closed """

    def reset(self):
        super().reset()
        self.tagstack.clear()

    def taglist(self, data, reset=True, depth_first=False):
        """ parse data and return found tag objects
        @param data:    html string
        @param reset:   reset state
        @param depth_first: return order: as opened (False), as closed (True), nested (None)
        @return: list of Tag objects
        """
        def flatten(_list, first=True):
            rlist = _list if first or not depth_first else itertools.chain(_list[1:], _list[:1])
            for item in rlist:
                if isinstance(item, list):
                    yield from flatten(item, first=False)
                else:
                    yield item

        if reset:
            self.reset()
        with contextlib.suppress(HTMLTagParser.AbortException):
            self.feed(data)
        if self.STRICT and self.tagstack:
            orphans = ', '.join(map(repr, map(str, orderedSet(self.tagstack, lazy=True))))
            raise compat_HTMLParseError(f'unclosed tag {orphans}')
        taglist = self._nestedtags[0] if depth_first is None else list(flatten(self._nestedtags[0]))
        self._nestedtags = [[]]
        return taglist

    def updatepos(self, i, j):
        offset = self._offset = super().updatepos(i, j)
        return offset

    def handle_starttag(self, tag, attrs):
        try:
            # we use internal variable for performance reasons
            tag_text = getattr(self, '_HTMLParser__starttag_text')
        except AttributeError:
            tag_text = HTMLTagParser.ANY_TAG_REGEX.match(self.rawdata[self._offset:]).group()

        tag_obj = tag
        tag_is_open = not (tag_text.endswith('/>') or tag in self.VOID_TAGS)
        if self.predicate(tag, attrs):
            tag_obj = self.Tag(tag, string=self.rawdata, attrs=attrs)
            tag_obj.openrange(self._offset, len(tag_text))
            nesting = [tag_obj]
            self._nestedtags[-1].append(nesting)
            if tag_is_open:
                self._nestedtags.append(nesting)
            else:
                self.callback(tag_obj)
        if tag_is_open:
            self.tagstack.appendleft(tag_obj)

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if '<' in tag:
            if self.STRICT:
                raise compat_HTMLParseError(f'malformed closing tag {tag!r}')
            tag = tag[:tag.index('<')]

        try:
            idx = self.tagstack.index(tag)
            if self.STRICT and idx:
                open_tags = ''.join(f'</{tag}>' for tag in itertools.islice(self.tagstack, idx))
                raise compat_HTMLParseError(
                    f'malnested closing tag {tag!r}, expected after {open_tags!r}')
            tag_obj = self.tagstack[idx]
            self.tagstack.remove(tag)
            if isinstance(tag_obj, self.Tag):
                tag_obj.closerange(slice(self._offset, self.rawdata.find('>', self._offset) + 1))
                self._nestedtags.pop()
                self.callback(tag_obj)
        except ValueError as exc:
            if isinstance(exc, compat_HTMLParseError):
                raise
            if self.STRICT:
                raise compat_HTMLParseError(f'stray closing tag {tag!r}') from exc


class MatchingElementParser(HTMLTagParser):
    """ optimized version of HTMLTagParser
    """
    def __init__(self, matchfunc):
        super().__init__()
        self.matchfunc = matchfunc
        self.found_none = True

    def reset(self):
        super().reset()
        self.found_none = True

    def callback(self, tag_obj):
        raise self.AbortException()

    def predicate(self, tag, attrs):
        if self.found_none and self.matchfunc(tag, attrs):
            self.found_none = False
            return True
        return False

    @staticmethod
    def class_value_regex(class_name):
        return rf'[\w\s\-]*(?<![\w\-]){re.escape(class_name)}(?![\w\-])[\w\s\-]*'

    @staticmethod
    def matching_tag_regex(tag, attribute, value_regex, escape=True):
        if isinstance(value_regex, re.Pattern):
            value_regex = value_regex.pattern
        elif escape:
            value_regex = re.escape(value_regex)

        return rf'''(?x)
            <(?i:{tag})
             (?:\s(?:[^>"'\\]|"[^"\\]*"|'[^'\\]*')*)?
             \s{re.escape(attribute)}\s*=\s*(?P<_q>['"])(?-x:{value_regex})(?P=_q)
            '''

    @classmethod
    def iter_tags(cls, regex, html, *, matchfunc):
        ignored = HTMLIgnoreRanges(html)
        parser = cls(matchfunc)
        for match in re.finditer(regex, html):
            if match.start() not in ignored:
                yield from parser.taglist(html[match.start():], reset=True)

    @classmethod
    def tags_by_name(cls, tag, html):
        def matchfunc(tag_str, _attrs):
            return tag_str == tag

        tag_regex = rf'''<\s*(?i:{re.escape(tag)})(?:\s(?:[^>"'\\]|"[^"\\]*"|'[^'\\]*')*)?>'''
        yield from cls.iter_tags(tag_regex, html, matchfunc=matchfunc)

    @classmethod
    def tags_by_attribute(cls, attribute, value, html, *, tag=r'[\w:.-]+', escape_value=True):
        def matchfunc(_tag_str, attrs):
            return any(attr == attribute and re.fullmatch(value, value_str)
                       for attr, value_str in attrs)

        tag_regex = cls.matching_tag_regex(tag, attribute, value, escape_value)
        yield from cls.iter_tags(tag_regex, html, matchfunc=matchfunc)

    @classmethod
    def extract_attributes(cls, html):
        attr_dict = {}

        def matchfunc(_tag, attrs):
            attr_dict.update(attrs)
            raise cls.AbortException()

        with contextlib.suppress(cls.AbortException):
            cls(matchfunc).feed(html)

        return attr_dict

    @classmethod
    def get_elements_text_and_html_by_tag(cls, tag, html):
        return [tag.text_and_html() for tag in cls.tags_by_name(tag, html)]

    @classmethod
    def get_element_text_and_html_by_tag(cls, tag, html):
        tag = next(cls.tags_by_name(tag, html), None)
        return tag and tag.text_and_html()

    @classmethod
    def get_elements_text_and_html_by_attribute(cls, *args, **kwargs):
        return [tag.text_and_html() for tag in cls.tags_by_attribute(*args, **kwargs)]

    @classmethod
    def get_elements_by_attribute(cls, *args, **kwargs):
        return [tag.text() for tag in cls.tags_by_attribute(*args, **kwargs)]

    @classmethod
    def get_elements_html_by_attribute(cls, *args, **kwargs):
        return [tag.html() for tag in cls.tags_by_attribute(*args, **kwargs)]

    @classmethod
    def get_element_by_attribute(cls, *args, **kwargs):
        tag = next(cls.tags_by_attribute(*args, **kwargs), None)
        return tag and tag.text()

    @classmethod
    def get_element_html_by_attribute(cls, *args, **kwargs):
        tag = next(cls.tags_by_attribute(*args, **kwargs), None)
        return tag and tag.html()

    @classmethod
    def get_elements_by_class(cls, class_name, html):
        value = cls.class_value_regex(class_name)
        return [tag.text() for tag
                in cls.tags_by_attribute('class', value, html, escape_value=False)]

    @classmethod
    def get_elements_html_by_class(cls, class_name, html):
        value = cls.class_value_regex(class_name)
        return [tag.html() for tag
                in cls.tags_by_attribute('class', value, html, escape_value=False)]

    @classmethod
    def get_elements_text_and_html_by_class(cls, class_name, html):
        value = cls.class_value_regex(class_name)
        return [tag.text_and_html() for tag
                in cls.tags_by_attribute('class', value, html, escape_value=False)]

    @classmethod
    def get_element_html_by_class(cls, class_name, html):
        value = cls.class_value_regex(class_name)
        tag = next(cls.tags_by_attribute('class', value, html, escape_value=False), None)
        return tag and tag.html()

    @classmethod
    def get_element_by_class(cls, class_name, html):
        value = cls.class_value_regex(class_name)
        tag = next(cls.tags_by_attribute('class', value, html, escape_value=False), None)
        return tag and tag.text()
