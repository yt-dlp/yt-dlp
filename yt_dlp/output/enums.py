import enum

from .hoodoo import Color, TermCode, Typeface
from ..utils import Namespace


class LogLevel(enum.Enum):
    """
    Represents a LogLevel

    Each LogLevel has a dedicated output in the Logger mapping.
    """
    SCREEN = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


class Verbosity(enum.Enum):
    """
    Represents a Verbosity

    Verbosity acts as a filter for certain logging events.
    """
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2


class Style(metaclass=Namespace):
    """A class holding generic styles"""
    HEADER = TermCode.make(Color.YELLOW)
    EMPHASIS = TermCode.make(Color.LIGHT | Color.BLUE)
    FILENAME = TermCode.make(Color.GREEN)
    ID = TermCode.make(Color.GREEN)
    DELIM = TermCode.make(Color.BLUE)
    ERROR = TermCode.make(Color.RED)
    WARNING = TermCode.make(Color.YELLOW)
    SUPPRESS = TermCode.make(Color.LIGHT | Color.BLACK)


class ProgressStyle(metaclass=Namespace):
    """A class holding Styles for progress formatting"""
    DOWNLOADED_BYTES = TermCode.make(Color.LIGHT | Color.BLUE)
    PERCENT = TermCode.make(Color.LIGHT | Color.BLUE)
    ETA = TermCode.make(Color.YELLOW)
    SPEED = TermCode.make(Color.GREEN)
    ELAPSED = TermCode.make(Typeface.BOLD, Color.WHITE)
    TOTAL_BYTES = TermCode()
    TOTAL_BYTES_ESTIMATE = TermCode()
