"""
A module providing simple abstractions for terminal codes

It replaces the previous (mini)curses module.
"""

import enum

CSI = '\x1B['
OSC = '\x1B]'
BEL = '\x07'
COLOR_END = 'm'

ERASE_LINE = f'{CSI}K'


class Color(enum.IntFlag):
    """
    A class representing a terminal color

    Used for `TermCode.make(...)` to provide a color code.

    `OR`ing with `Color.LIGHT` indicates that the color should be a lighter color.
    Similarly, `OR`ing with `Color.BG` indicates that the color should be in the background.
    Both can be combined to create a light background color,
    so `Color.BG | Color.LIGHT | Color.BLUE` will give a light blue background.
    """
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
    """
    A class representing a terminal typeface

    Used for `TermCode.make(...)` to provide a typeface code.
    """
    BOLD = '1'
    UNDERLINED = '4'
    NEGATIVE = '7'


class TermCode(str):
    """A string wrapper representing a terminal code"""

    def __repr__(self):
        return f'{type(self).__name__}({str(self)!r})'

    @classmethod
    def make(cls, *text_formats):
        """
        Creates a TermCode from the provided text formats

        This method combines multiple `Color`s and `Typeface`s into one code.
        Codes are prefixed by `CSI` and suffixed by `COLOR_END`.

        @params text_formats    A `Typeface`/`Color` specifying the format.

        @returns                A `TermCode` combining the specified formats.
        """
        sequence = ';'.join(map(cls._convert_color, text_formats))
        return cls(f'{CSI}{sequence}{COLOR_END}')

    @classmethod
    def join(cls, *text_formats):
        """
        Joins multiple terminal codes into one

        `Color`s and `Typeface`s will be converted to their respective codes.
        Multiple CSI sequences will be joined into one
        while other sequences will be left untouched.

        @params text_formats    A text format which could be either:
                                - A `Typeface`/`Color` for color formatting.
                                - A `str`/`TermCode` for providing direct terminal codes.

        @returns                A `TermCode` combining the specified text formats.
        """
        if len(text_formats) == 1 and isinstance(text_formats[0], str):
            return cls(text_formats[0])

        codes = []

        is_color = False
        for text_format in text_formats:
            if isinstance(text_format, (Color, Typeface)):
                codes.append(';' if is_color else CSI)
                is_color = True
                codes.append(cls._convert_color(text_format))

            # isinstance(text_format, (str, TermCode))
            elif text_format.startswith(CSI) and text_format.endswith(COLOR_END):
                codes.append(';' if is_color else CSI)
                is_color = True
                codes.append(text_format[len(CSI):-len(COLOR_END)])

            else:
                if is_color:
                    codes.append(COLOR_END)
                    is_color = False
                codes.append(text_format)

        if is_color:
            codes.append(COLOR_END)

        return cls(''.join(codes))

    @staticmethod
    def _convert_color(text_format):
        if isinstance(text_format, Typeface):
            return text_format.value

        # isinstance(text_format, Color)
        prefix = 30

        if text_format & Color.LIGHT:
            prefix += 60
            text_format ^= Color.LIGHT

        if text_format & Color.BG:
            prefix += 10
            text_format ^= Color.BG

        return str(prefix + text_format)


RESET = TermCode(f'{CSI}0{COLOR_END}')


def format_text(message, *text_formats):
    """
    Format text using the provided text format

    Resets the changes afterwards by appending the reset sequence.
    Joins multiple sequences through `TermCode.join(...)`.

    @params text_formats    A `TermCode`/`Typeface`/`Color`/`str` specifying the format.
    """
    return f'{TermCode.join(*text_formats)}{message}{RESET}'


def move_cursor(distance):
    """
    Make a vertical cursor movement sequence

    @param distance The vertical amount of columns to move the cursor by.
                    Negative moves up, positive down.
    """
    if not distance:
        return ''

    elif distance > 0:
        return '\n' * distance

    elif distance == -1:
        return f'\r{CSI}A'

    else:
        return f'\r{CSI}{-distance}A'
