import json
import math
import operator
import re
import string
import time
import unicodedata
from functools import partial

from ._utils import (
    IDENTITY,
    NUMBER_RE,
    LazyList,
    escapeHTML,
    float_or_none,
    format_decimal_suffix,
    int_or_none,
    try_call,
    unified_timestamp,
    variadic,
)
from .traversal import traverse_obj
from ..compat import compat_shlex_quote

_OPERATOR_STR = {
    operator.add: "+",
    operator.sub: "-",
}
_MATH_OPERATORS = dict(map(reversed, _OPERATOR_STR.items()))


class Formatter:
    def __init__(self, fmt):
        self.fmt = fmt

    def __repr__(self):
        return f"{type(self).__name__}({self.fmt!r})"


class StringFormatter(Formatter):
    def __call__(self, data, sanitize):
        # Convert to numerical format before trying to use data
        conversion = self.fmt[-1]
        if conversion in 'diouxX':
            data = int_or_none(data)
        elif conversion in 'eEdDgG':
            data = float_or_none(data)

        return None if data is None else self.fmt % data


def _dumpjson_default(obj):
    if isinstance(obj, (set, LazyList)):
        return list(obj)
    return repr(obj)


class CustomFormatter:
    def __init__(self, conversion, flags, width, precision):
        self._conversion = conversion
        self._flags = flags
        self._width = width
        self._precision = precision

    def __call__(self, data, sanitize):
        if data is None:
            return None

        if self._conversion == "l":
            delim = '\n' if '#' in self._flags else ', '
            data = delim.join(map(str, variadic(data, allowed_types=(str, bytes))))
        elif self._conversion == 'j':  # json
            data = json.dumps(
                data, default=_dumpjson_default,
                indent=4 if '#' in self._flags else None, ensure_ascii='+' not in self._flags)
        elif self._conversion == 'h':  # html
            data = escapeHTML(str(data))
        elif self._conversion == 'q':  # quoted
            data = map(str, variadic(data) if '#' in self._flags else [data])
            data = ' '.join(map(compat_shlex_quote, data))
        elif self._conversion == 'B':  # bytes
            data = f'%{str_fmt}'.encode() % str(data).encode()
            return data.decode('utf-8', 'ignore')
        elif self._conversion == 'U':  # unicode normalized
            # "+" = compatibility equivalence, "#" = NFD
            fmt = 'NF'
            if '+' in self._flags:
                fmt += 'K'
            fmt += 'D' if '#' in self._flags else 'C'
            data = unicodedata.normalize(fmt, data)
        elif self._conversion == 'D':  # decimal suffix
            num_fmt = fmt[:-1].replace('#', '')
            data = format_decimal_suffix(
                data, f'%{num_fmt}f%s' if num_fmt else '%d%s',
                factor=1024 if '#' in self._flags else 1000)
        elif self._conversion == 'S':  # filename sanitization
            data = filename_sanitizer(last_field, data, restricted='#' in self._flags)
        elif self._conversion == 'c':
            if data:
                data = str(data)[0]
            return ''

        return f"c{data!r}"

    def __repr__(self):
        args = (self._conversion, self._flags, self._width, self._precision)
        return f"{type(self).__name__}{args}"


class DateFormatter(Formatter):
    def __call__(self, data, sanitize):
        if isinstance(data, str):
            data = unified_timestamp(data)

        if data is None:
            return None

        if isinstance(data, (int, float)):
            data = time.gmtime(data)

        return time.strftime(self.fmt, data)


class _SanitizingFormatter(string.Formatter):
    def __init__(self, sanitize):
        self.sanitize = sanitize

    def format_field(self, value, format_spec):
        return self.sanitize(super().format_field(value, format_spec))

    def convert_field(self, value, conversion):
        return self.sanitize(super().convert_field(value, conversion))


class SanitizingReplacer(Formatter):
    def __call__(self, data, sanitize):
        if data is None:
            return None

        return try_call(_SanitizingFormatter(sanitize).format, args=(self.fmt, data))


class Traverse:
    def __init__(self, paths):
        self._paths = paths

    def __call__(self, data, sanitize):
        return traverse_obj(data, self._paths, is_user_input=True, traverse_string=True)

    def __repr__(self):
        return f"{type(self).__name__}({self._paths})"


class Math:
    def __init__(self, traversals):
        self.traversals = traversals

    def __call__(self, data, sanitize):
        result = 0

        for op, traversal in self.traversals:
            value = traversal(data, sanitize) if callable(traversal) else traversal
            result = op(result, number(value))

        return result

    def __str__(self):
        (op, traversal), *remaining = self.traversals
        prefix = "-" if op is operator.sub else ""
        values = "".join(f" {_OPERATOR_STR[op]} {traversal}" for op, traversal in remaining)
        return f"{prefix}{traversal}{values}"

    def __repr__(self):
        return f"{type(self).__name__}({self.traversals})"


class Composer:
    def __init__(self, *functions):
        self.functions = functions

    def __call__(self, data, sanitize):
        for func in self.functions:
            data = func(data, sanitize)

        return data

    def __str__(self):
        return " . ".join(map(str, self.functions)).join("()")

    def __repr__(self):
        funcs = ", ".join(map(repr, self.functions))
        return f"{type(self).__name__}({funcs})"


def number(value):
    result = int_or_none(value)
    if result is None:
        result = float_or_none(value)
        if result is None:
            result = math.nan

    return result


class Alternate:
    def __init__(self, *functions):
        self.functions = functions

    def __call__(self, data, sanitize):
        for function in self.functions:
            result = function(data, sanitize)
            if result is not None:
                return result

        return None

    def __str__(self):
        return " | ".join(map(str, self.functions)).join("()")

    def __repr__(self):
        return f"{type(self).__name__}({self.functions!r})"


class Defaulter(Formatter):
    def __call__(self, data, sanitize):
        return self.fmt if data is None else data


class Sanitizer:
    def __call__(self, data, sanitize):
        return sanitize(data)

    def __repr__(self):
        return f"{type(self).__name__}()"


def compose(functions):
    return Composer(*functions) if len(functions) > 1 else functions[0]


SANITIZER = Sanitizer()


class OutputTemplate:
    # TODO: implement converter interface
    CUSTOM_CONVERTERS = {
        letter: partial(CustomFormatter, letter)
        for letter in "BjhlqDSU"}
    # Ref: <https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting>
    # TODO: Error correction capturing groups
    _PRINTF_REGEX = re.compile(r"""
        %%|%\((?P<key>[^)]+)\)
        (?P<flags>[#0\- +]*)
        (?P<width>\d*)  # `*` is not valid
        (?P<precision>(?:\.\d+)?)  # `*` is not valid
        (?:[hlL])?  # length modifier, unused
        (?P<conversion>[diouxXeEfFgGcrsa{}]) # % is invalid
    """.format(re.escape("".join(CUSTOM_CONVERTERS))), re.VERBOSE)

    _FIELD_INNER_RE = r"(?:\w+|%(num)s|%(num)s?(?::%(num)s?){1,2})" % {
        "num": r"(?:-?\d+)",
    }
    _FIELD_RE = r"\w*(?:\.(?:%(inner)s|{%(field)s(?:,%(field)s)*}))*" % {
        "inner": _FIELD_INNER_RE,
        "field": rf"\w*(?:\.{_FIELD_INNER_RE})*",
    }
    _MATH_OPERATORS = {
        '+': operator.add,
        '-': operator.sub,
    }
    # _KEY_REGEX = re.compile(rf"({_FIELD_RE})(?:&([^|]*))?(?:\|(.*))?")
    _KEY_REGEX = re.compile(r'''
        (?P<negate>-)?
        (?P<fields>%(field)s)
        (?P<maths>(?:
            (?:%(operator)s)
            (?:%(math_field)s)
        )*)
        (?:>(?P<date_format>.+?))?
        (?P<key>(?<!\\),[^|&)]+)?
        (?:&(?P<replacement>.*?))?
        (?:\|(?P<default>.*?))?
        $''' % {
        "field": _FIELD_RE,
        "operator": "|".join(map(re.escape, _MATH_OPERATORS)),
        "math_field": rf'{_FIELD_RE}|-?{NUMBER_RE}',
    }, re.DOTALL | re.VERBOSE)
    DEFAULT = "NA"

    def __init__(self, parts):
        self.parts = parts

    @classmethod
    def from_string(cls, template):
        result = []
        position = 0
        for match in cls._PRINTF_REGEX.finditer(template):
            assert match
            if position != match.start():
                result.append(template[position:match.start()])

            position = match.end()
            if match[0] == '%%':
                result.append('%')
                continue

            key, flags, width, precision, conversion = match.groups()
            converter = cls.CUSTOM_CONVERTERS.get(conversion)
            if converter:
                conversion_function = converter(flags, width, precision)
            else:
                fmt = f"%{flags}{width}{precision or ''}{conversion}"
                conversion_function = StringFormatter(fmt)

            result.append(cls._process_key(key, conversion_function))

        if position != len(template):
            result.append(template[position:])

        print(f"{result=}")

        return cls(result)

    @classmethod
    def _process_key(cls, key, conversion_function):
        # traversal => conversion => replacement => default => sanitize
        # traversal = path, math, date_format | ...
        alternates = []

        replacement = None
        default = None

        while key:
            match = cls._KEY_REGEX.fullmatch(key)
            print(f"{key=}")
            if not match:
                # TODO: better error messages as fallback
                message = f"Invalid key: {key!r}"
                if ".." in key:
                    message = f"{message} (Potentially duplicate `.`?)"
                raise ValueError(message)
            negate, fields, maths, date_format, key, replacement, default = match.groups()
            path = []

            path.append(cls._build_traversal(fields))
            if date_format:
                path.append(DateFormatter(date_format))
            # TODO: implement maths

            alternates.append(compose(path))

        funcs = [Alternate(alternates) if len(alternates) > 1 else alternates[0], conversion_function]
        sanitize = True
        if replacement:
            # replacement formatter will sanitize the field internally
            sanitize = False
            funcs.append(SanitizingReplacer(replacement))

        funcs.append(Defaulter(default if default is not None else cls.DEFAULT))
        if sanitize:
            funcs.append(SANITIZER)

        print(f"{replacement=}\n{default=}\n{sanitize=}")

        return compose(funcs)

    @classmethod
    def _build_traversal(cls, fields):
        path = fields.split('.')
        print(f"{path=}")
        return Traverse(path)

    def evaluate(self, data, sanitize=IDENTITY):
        return "".join(
            part if isinstance(part, str) else part(data, sanitize)
            for part in self.parts)

    def __mod__(self, data):
        return self.evaluate(data)
