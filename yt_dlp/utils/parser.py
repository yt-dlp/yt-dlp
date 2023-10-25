from __future__ import annotations

import re
import string


def create_matcher(separators: str):
    specials = re.escape(separators)

    main_re = re.compile(rf'(?:\\[\\{specials}]|[^\\{specials}])+')
    escape_re = re.compile(rf'\\([{specials}])')

    def matcher(data: str, begin: int) -> tuple[int, str | None]:
        match = main_re.match(data, begin)
        if not match:
            return begin, None

        return match.end(), escape_re.sub(r'\g<1>', match[0])

    return staticmethod(matcher)


class ParseError(Exception):
    def __init__(self, msg: str, offset: int):
        self.msg = msg
        self.offset = offset

    def __str__(self):
        return f'{self.msg} (at {self.offset})'

    def __repr__(self):
        return f'{type(self).__name__}({self.msg!r}, {self.offset!r})'


class Parser:
    _BEGIN_RE = re.compile(r'%(\()')
    _END_RE = re.compile(
        r'''
        (?P<flags>[#0\- +]*)
        (?P<width>\d*)  # `*` is not valid
        (?P<precision>(?:\.\d*)?)  # `*` is not valid
        ''', re.VERBOSE)
    _MATCH_FIELD = create_matcher('+-.{}>,&|)')
    _MATCH_DATE_FORMAT = create_matcher(',&|)')
    _MATCH_REPLACEMENT = create_matcher('|)')
    _MATCH_DEFAULT = create_matcher(')')

    @classmethod
    def parse(cls, data: str):
        length = len(data)
        index = 0
        results = []

        for match in cls._BEGIN_RE.finditer(data, index):
            if not match.group(1):
                continue
            end = match.start()
            if index != end:
                results.append(data[index:end].replace('%%', '%'))

            index = match.end()
            try:
                index, result = cls._read_key(data, index)
            except IndexError:
                raise ParseError('Unclosed \'(\'', index) from None

            results.append(result)
            end_match = cls._END_RE.match(data, index)
            assert end_match, '_END_RE should be completely optional'
            flags, width, precision = end_match.group('flags', 'width', 'precision')
            # TODO: implement flags

            index = end_match.end()
            try:
                next_char = data[index]
            except IndexError:
                raise ParseError('Missing conversion', index) from None

            index += 1
            if next_char in string.ascii_letters:
                if next_char not in 'diouxXeEfFgGcrsa':
                    raise ParseError(f'Unknown conversion: {next_char!r}', index)
            else:
                raise ParseError(f'Unexpected character {next_char!r}, are you missing a conversion?', index)

        if index != length:
            results.append(data[index:].replace('%%', '%'))

        return results

    @classmethod
    def _read_key(cls, data, index):
        results = []
        traversal = []
        in_dict_traversal = False
        last_was_dot = False

        while True:
            index, result = cls._MATCH_FIELD(data, index)
            if result is not None:
                traversal.append(result)

            next_char = data[index]
            index += 1
            if next_char != '.':
                last_was_dot = False

            if next_char == ')':
                if in_dict_traversal:
                    raise ParseError('Unexpected key end, did you forget a \'}\'?', index)
                if traversal:
                    results.append(traversal)
                return index, results

            elif next_char == '.':
                if last_was_dot:
                    raise ParseError('Unexpected \'.\', did you add an additional \'.\'?', index)

                last_was_dot = True
                if in_dict_traversal:
                    raise ParseError('Unexpected \'.\', did you forget a \'}\'?', index)

            elif next_char == ',':
                if in_dict_traversal:
                    continue
                results.append(traversal)
                traversal = []

            elif next_char == '{':
                if in_dict_traversal:
                    raise ParseError('Unexpected nested \'{\', did you forget a \'}\'?', index)
                in_dict_traversal = True

            elif next_char == '}':
                if not in_dict_traversal:
                    raise ParseError('Unexpected \'}\', did you forget a \'{\'?', index)
                in_dict_traversal = False
                results.append({item: item for item in traversal})
                traversal.clear()

            else:  # TODO: date (>), maths (+-), replacement (&) and default (|)
                raise ParseError(f'Parser case not implemented: \'{next_char}\'', index)


if __name__ == '__main__':
    tests = [
        # fail
        R'%(a,b}s',
        R'%(a,{b}s',
        R'%(a,{b})',
        R'%(a,{b)s',
        R'%(a,{b})---+# 0 #+---',
        R'%(a,{b}))',
        R'%(a,{b})z',
        R'%(a,{b.c})s',
        R'%(a,{b}.c})s',
        R'%(a..b)s',
        R'%(a.{{b}}.c)s',
        R'%(test&({}))s',
        R'%(test|())s',
        # pass
        R'%(a,b)s [%(id)s].%(ext)s',
        R'%(a\{b\}c.test)s',
        R'%(test.{id,test})s',
        R'%({id,test})s',
        # pleb parser implementation
        R'%(test|(\))s',
        R'%(a>datefmt)s',
        R'%(test&({}\))s',
        R'%(+a-2)s',
        R'%(a-2)s',
    ]

    for test in tests:
        offset = 0
        try:
            results = Parser.parse(test)
        except ParseError as error:
            prefix = 'FAIL: Invalid output template: '
            symbol = '^'
            offset += error.offset
            results = f' {error.msg}'
        else:
            prefix = 'PASS: '
            symbol = ''

        print(f'{prefix}{test}\n{symbol: >{offset + len(prefix)}}{results}')
