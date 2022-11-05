import enum

CSI = '\x1B['
OSC = '\x1B]'
BEL = '\x07'


class Color(enum.IntFlag):
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7

    LIGHT = 1 << 3
    BG = 1 << 4


class Typeface(enum.Enum):
    BOLD = 1
    UNDERLINED = 4
    NEGATIVE = 7


class TermCode(str):
    def __new__(cls, *text_formats):
        code = ''.join(
            text_format if isinstance(text_format, str) else make_color_code(text_format)
            for text_format in text_formats)
        return super().__new__(cls, code)

    def __repr__(self):
        return f'{type(self).__name__}({str(self)!r})'


def make_color_code(*text_formats):
    result = []

    for text_format in text_formats:
        if isinstance(text_format, Typeface):
            result.extend(f'{CSI}{text_format.value}m')

        elif isinstance(text_format, Color):
            prefix = 3

            if text_format & Color.LIGHT:
                prefix += 6
                text_format ^= Color.LIGHT

            if text_format & Color.BG:
                prefix += 1
                text_format ^= Color.BG

            result.append(f'{CSI}{prefix}{text_format}m')

        else:  # isinstance(text_format, TermCode)
            result.append(text_format)

    return ''.join(result)


def format_text(message, *text_formats):
    return f'{make_color_code(*text_formats)}{message}{CSI}0m'
