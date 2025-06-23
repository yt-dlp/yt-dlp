"""
A partial parser for WebVTT segments. Interprets enough of the WebVTT stream
to be able to assemble a single stand-alone subtitle file, suitably adjusting
timestamps on the way, while everything else is passed through unmodified.

Regular expressions based on the W3C WebVTT specification
<https://www.w3.org/TR/webvtt1/>. The X-TIMESTAMP-MAP extension is described
in RFC 8216 §3.5 <https://tools.ietf.org/html/rfc8216#section-3.5>.
"""

import io
import re

from .utils import int_or_none, timetuple_from_msec


class _MatchParser:
    """
    An object that maintains the current parsing position and allows
    conveniently advancing it as syntax elements are successfully parsed.
    """

    def __init__(self, string):
        if not isinstance(string, str):
            raise TypeError('Expected string input to _MatchParser')
        self._data = string
        self._pos = 0

    def match(self, r):
        if isinstance(r, re.Pattern):
            return r.match(self._data, self._pos)
        if isinstance(r, str):
            if self._data.startswith(r, self._pos):
                return len(r)
            return None
        raise ValueError(f'Expected regex or string, got {type(r).__name__}')

    def advance(self, by):
        if by is None:
            amt = 0
        elif isinstance(by, re.Match):
            amt = len(by.group(0))
        elif isinstance(by, str):
            amt = len(by)
        elif isinstance(by, int):
            amt = by
        else:
            raise ValueError(f'Unsupported advance type: {type(by).__name__}')
        self._pos += amt
        return by

    def consume(self, r):
        return self.advance(self.match(r))

    def child(self):
        return _MatchChildParser(self)


class _MatchChildParser(_MatchParser):
    """
    A child parser state, which advances through the same data as
    its parent, but has an independent position. This is useful when
    advancing through syntax elements we might later want to backtrack
    from.
    """

    def __init__(self, parent):
        super().__init__(parent._data)
        self.__parent = parent
        self._pos = parent._pos

    def commit(self):
        """
        Advance the parent state to the current position of this child state.
        """
        self.__parent._pos = self._pos
        return self.__parent


class ParseError(Exception):
    def __init__(self, parser):
        data = parser._data[parser._pos:parser._pos + 100]
        super().__init__(f'Parse error at position {parser._pos} (near {data!r})')


# While the specification <https://www.w3.org/TR/webvtt1/#webvtt-timestamp>
# prescribes that hours must be *2 or more* digits, timestamps with a single
# digit for the hour part has been seen in the wild.
# See https://github.com/yt-dlp/yt-dlp/issues/921
_REGEX_TS = re.compile(r'''(?x)
    (?:([0-9]{1,}):)?
    ([0-9]{2}):
    ([0-9]{2})\.
    ([0-9]{3})?
''')
_REGEX_EOF = re.compile(r'\Z')
_REGEX_NL = re.compile(r'(?:\r\n|[\r\n]|$)')
_REGEX_BLANK = re.compile(r'(?:\r\n|[\r\n])+')
_REGEX_OPTIONAL_WHITESPACE = re.compile(r'[ \t]*')


def _parse_ts(ts):
    """
    Convert a parsed WebVTT timestamp (a re.Match obtained from _REGEX_TS)
    into an MPEG PES timestamp: a tick counter at 90 kHz resolution.
    """
    if ts is None or not isinstance(ts, re.Match):
        raise ValueError('Invalid timestamp match for _parse_ts')
    return 90 * sum(
        int(part or 0) * mult for part, mult in zip(ts.groups(), (3600_000, 60_000, 1000, 1)))


def _format_ts(ts):
    """
    Convert an MPEG PES timestamp into a WebVTT timestamp.
    This will lose sub-millisecond precision.
    """
    return '%02u:%02u:%02u.%03u' % timetuple_from_msec(int((ts + 45) // 90))


class Block:
    """
    An abstract WebVTT block.
    """

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @classmethod
    def parse(cls, parser):
        m = parser.match(cls._REGEX)
        if not m:
            return None
        parser.advance(m)
        return cls(raw=m.group(0))

    def write_into(self, stream):
        stream.write(self.raw)


class HeaderBlock(Block):
    """
    A WebVTT block that may only appear in the header part of the file,
    i.e. before any cue blocks.
    """
    pass


class Magic(HeaderBlock):
    _REGEX = re.compile(r'\ufeff?WEBVTT([ \t][^\r\n]*)?(?:\r\n|[\r\n])')

    _REGEX_TSMAP = re.compile(r'X-TIMESTAMP-MAP=')
    _REGEX_TSMAP_LOCAL = re.compile(r'LOCAL:')
    _REGEX_TSMAP_MPEGTS = re.compile(r'MPEGTS:([0-9]+)')
    _REGEX_TSMAP_SEP = re.compile(r'[ \t]*,[ \t]*')
    _REGEX_META = re.compile(r'(?:(?!-->)[^\r\n])+:(?:(?!-->)[^\r\n])+(?:\r\n|[\r\n])')

    @classmethod
    def __parse_tsmap(cls, parser):
        parser = parser.child()
        local, mpegts = None, None

        while True:
            if parser.consume(cls._REGEX_TSMAP_LOCAL):
                m = parser.consume(_REGEX_TS)
                if not m:
                    raise ParseError(parser)
                local = _parse_ts(m)
            elif parser.consume(cls._REGEX_TSMAP_MPEGTS):
                m = parser.match(cls._REGEX_TSMAP_MPEGTS)
                if not m:
                    raise ParseError(parser)
                mpegts = int_or_none(m.group(1))
                if mpegts is None:
                    raise ParseError(parser)
                parser.advance(m)
            else:
                raise ParseError(parser)

            if parser.consume(cls._REGEX_TSMAP_SEP):
                continue
            if parser.consume(_REGEX_NL):
                break
            raise ParseError(parser)

        parser.commit()
        return local, mpegts

    @classmethod
    def parse(cls, parser):
        parser = parser.child()

        m = parser.consume(cls._REGEX)
        if not m:
            raise ParseError(parser)

        extra = m.group(1)
        local, mpegts, meta = None, None, ''
        while not parser.consume(_REGEX_NL):
            if parser.consume(cls._REGEX_TSMAP):
                local, mpegts = cls.__parse_tsmap(parser)
                continue
            m = parser.consume(cls._REGEX_META)
            if m:
                meta += m.group(0)
                continue
            raise ParseError(parser)
        parser.commit()
        return cls(extra=extra, mpegts=mpegts, local=local, meta=meta)

    def write_into(self, stream):
        stream.write('WEBVTT')
        if self.extra:
            stream.write(self.extra)
        stream.write('\n')
        if self.local is not None or self.mpegts is not None:
            stream.write('X-TIMESTAMP-MAP=LOCAL:')
            stream.write(_format_ts(self.local or 0))
            stream.write(',MPEGTS:')
            stream.write(str(self.mpegts or 0))
            stream.write('\n')
        if self.meta:
            stream.write(self.meta)
        stream.write('\n')


class StyleBlock(HeaderBlock):
    _REGEX = re.compile(r'''(?x)
        STYLE[\ \t]*(?:\r\n|[\r\n])
        ((?:(?!-->)[^\r\n])+(?:\r\n|[\r\n]))*
        (?:\r\n|[\r\n])
    ''')


class RegionBlock(HeaderBlock):
    _REGEX = re.compile(r'''(?x)
        REGION[\ \t]*
        ((?:(?!-->)[^\r\n])+(?:\r\n|[\r\n]))*
        (?:\r\n|[\r\n])
    ''')


class CommentBlock(Block):
    _REGEX = re.compile(r'''(?x)
        NOTE(?:\r\n|[\ \t\r\n])
        ((?:(?!-->)[^\r\n])+(?:\r\n|[\r\n]))*
        (?:\r\n|[\r\n])
    ''')


class CueBlock(Block):
    """
    A cue block. The payload is not interpreted.
    """

    _REGEX_ID = re.compile(r'((?:(?!-->)[^\r\n])+)(?:\r\n|[\r\n])')
    _REGEX_ARROW = re.compile(r'[ \t]+-->[ \t]+')
    _REGEX_SETTINGS = re.compile(r'[ \t]+((?:(?!-->)[^\r\n])+)')
    _REGEX_PAYLOAD = re.compile(r'[^\r\n]+(?:\r\n|[\r\n])?')

    @classmethod
    def parse(cls, parser):
        parser = parser.child()

        id_ = None
        m = parser.consume(cls._REGEX_ID)
        if m:
            id_ = m.group(1)

        m0 = parser.consume(_REGEX_TS)
        if not m0 or not parser.consume(cls._REGEX_ARROW):
            return None
        m1 = parser.consume(_REGEX_TS)
        if not m1:
            return None
        m2 = parser.consume(cls._REGEX_SETTINGS)
        parser.consume(_REGEX_OPTIONAL_WHITESPACE)
        if not parser.consume(_REGEX_NL):
            return None

        start = _parse_ts(m0)
        end = _parse_ts(m1)
        settings = m2.group(1) if m2 else None

        text = io.StringIO()
        while True:
            m = parser.consume(cls._REGEX_PAYLOAD)
            if not m:
                break
            text.write(m.group(0))

        parser.commit()
        return cls(id=id_, start=start, end=end, settings=settings, text=text.getvalue())


def parse_fragment(frag_content):
    """
    A generator that yields (partially) parsed WebVTT blocks when given
    a bytes object containing the raw contents of a WebVTT file.
    """
    if not isinstance(frag_content, (bytes, bytearray)):
        raise TypeError('Expected bytes for frag_content')

    parser = _MatchParser(frag_content.decode(errors='replace'))

    yield Magic.parse(parser)

    while not parser.match(_REGEX_EOF):
        if parser.consume(_REGEX_BLANK):
            continue
        block = RegionBlock.parse(parser)
        if block:
            yield block
            continue
        block = StyleBlock.parse(parser)
        if block:
            yield block
            continue
        block = CommentBlock.parse(parser)
        if block:
            yield block
            continue
        break

    while not parser.match(_REGEX_EOF):
        if parser.consume(_REGEX_BLANK):
            continue
        block = CommentBlock.parse(parser)
        if block:
            yield block
            continue
        block = CueBlock.parse(parser)
        if block:
            yield block
            continue
        raise ParseError(parser)
