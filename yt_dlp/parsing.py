import collections
import contextlib
import itertools
import re
from html.parser import HTMLParser

from .utils import orderedSet

from .compat import compat_HTMLParseError


class HTMLTagParser(HTMLParser):
    """HTML parser which acts as iterator
    returns found elements as instances of Tag
    nested elements will be returned before its parents

    strict=True raises compat_HTMLParseError on malformed html

    two modes of usage:
        # as an lazy iterator:
        for tag_obj in HTMLTagParser(html):
            tag_obj.text_and_html()

        # or return a list with all found tag objects
        # this is faster by factor 2-5 compared to iteration
        for tag_obj in HTMLTagParser(html).taglist():
            tag_obj.text_and_html()
    """

    STRICT = False
    ANY_TAG_REGEX = re.compile(r'''<(?:"[^"]*"|'[^']*'|[^"'>])*?>''')
    CLOSING_TAG_REGEX = re.compile(r'</\s*[^\s<>]+(?:\s*>)?')
    VOID_TAGS = {
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'keygen', 'link', 'meta', 'param', 'source', 'track', 'wbr',
    }

    class Tag:
        __slots__ = 'name', 'string', 'start', 'start_len', 'stop', 'attrs'

        def __init__(self, name, *, string='', start=None, stop=None, attrs=()):
            self.name = name
            self.string = string
            self.start = start
            self.start_len = 0
            self.stop = stop
            self.attrs = tuple(attrs)

        def __str__(self):
            return self.name

        def __repr__(self):
            return f'{self.__class__.__name__}({str(self)!r})'

        def __eq__(self, other):
            return self.name == other

        def html(self):
            return self.string[self.start:self.stop]

        def text_and_html(self):
            assert isinstance(self.start, int)
            if not self.start_len:
                match = HTMLTagParser.ANY_TAG_REGEX.match(self.string[self.start:])
                assert match
                self.start_len = len(match.group())
            if self.stop is None:
                return '', self.string[self.start: self.start + self.start_len]
            html = self.html()
            cidx = html.rindex('</')
            return html[self.start_len:cidx], html

    class EarlyExitException(Exception):
        pass

    def __init__(self):
        super().__init__()
        self.tagstack = collections.deque()
        self._offset = self.offset
        self.found_tags = []

    def predicate(self, tag, attrs):
        return True

    def callback(self, tag_obj):
        pass

    def abort(self, last_tag=None):
        if last_tag:
            self.found_tags.append(last_tag)
        raise HTMLTagParser.EarlyExitException()

    def taglist(self, data, reset=True):
        self.found_tags.clear()
        if reset:
            self.reset()
            self.tagstack.clear()
        with contextlib.suppress(HTMLTagParser.EarlyExitException):
            self.feed(data)
        if self.STRICT and self.tagstack:
            orphans = ', '.join(map(repr, map(str, orderedSet(self.tagstack, lazy=True))))
            raise compat_HTMLParseError(f'unclosed tag {orphans}')
        return self.found_tags

    def updatepos(self, i, j):
        offset = self._offset = super().updatepos(i, j)
        return offset

    def handle_starttag(self, tag, attrs):
        try:
            # we use internal variable for performance reason
            tag_text = getattr(self, '_HTMLParser__starttag_text')
        except AttributeError:
            tag_text = HTMLTagParser.ANY_TAG_REGEX.match(self.rawdata[self._offset:]).group()
        if self.predicate(tag, attrs):
            obj = self.Tag(
                tag, string=self.rawdata, start=self._offset, attrs=attrs)
            obj.start_len = len(tag_text)
            if tag_text.endswith('/>') or tag in self.VOID_TAGS:
                if self.callback(obj) is not False:
                    self.found_tags.append(obj)
                return
        else:
            obj = None

        self.tagstack.appendleft(obj or tag)

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
            if not isinstance(tag_obj, str):
                # since we landed here we'll always find a closing tag
                match = self.CLOSING_TAG_REGEX.match(self.rawdata[self._offset:])
                tag_obj.stop = self._offset + match.end()
                if self.callback(tag_obj) is not False:
                    self.found_tags.append(tag_obj)
        except ValueError as exc:
            if isinstance(exc, compat_HTMLParseError):
                raise
            elif self.STRICT:
                raise compat_HTMLParseError(f'stray closing tag {tag!r}')


class ClassParser(HTMLTagParser):
    def __init__(self, attribute, matchfunc, stop):
        super().__init__()
        self.search_attr = attribute
        self.matchfunc = matchfunc
        self.stop = stop
        self.processing = 0

    def predicate(self, tag, attrs):
        if self.processing <= 0 and self.stop is not None and self._offset > self.stop:
            self.abort()
        string = dict(attrs).get(self.search_attr, '')
        if self.matchfunc(string):
            self.processing += 1
            return True
        return False

    def callback(self, tag_obj):
        if self.stop is None:
            self.abort(tag_obj)
        self.processing -= 1

    @classmethod
    def get_elements_html_by_class(cls, class_name, html):
        regex = re.compile(rf'[\w\- ]*\b{re.escape(class_name)}\b')
        it = re.finditer(rf'<.+ class=[\'"]{regex.pattern}', html)
        start = stop = None
        for match in it:
            if start is None:
                start = match.start()
            else:
                stop = match.end()
        if start is None:
            return []
        parser = cls('class', lambda x: regex.match(x), stop)
        return [tag.html() for tag in parser.taglist(html[start:])]


class FirstMatchingElementParser(HTMLTagParser):
    def __init__(self, matchfunc):
        super().__init__()
        self.matchfunc = matchfunc
        self.found = False

    def predicate(self, tag, attrs):
        if not self.found and self.matchfunc(tag, attrs):
            self.found = True
            return True
        return False

    def callback(self, obj):
        self.abort(obj)

    @classmethod
    def get_element_text_and_html_by_tag(cls, tag, html):
        """
        For the first element with the specified tag in the given HTML document
        return its content (text) and the whole element (html)
        """
        parser = cls(lambda _tag, _: _tag == tag)
        for tag_obj in parser.taglist(html):
            return tag_obj.text_and_html()
        raise compat_HTMLParseError(f'tag {tag} not found')
