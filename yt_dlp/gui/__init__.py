"""Graphical interface for yt-dlp

It is built on tkinter so that it is available in any standard CPython
installation and can be frozen without pulling in extra runtime dependencies.
"""

from __future__ import annotations

import sys

from ..version import __version__

__all__ = ['main']

USAGE = 'Usage: yt-dlp-gui [URL]...'

MISSING_TKINTER = (
    'ERROR: tkinter is not available in this Python installation.\n'
    'Install the Tk bindings of your platform (python3-tk on Debian/Ubuntu, '
    'python-tk on Homebrew) or use the standalone yt-dlp GUI build.')


def report(message):
    """Write `message` to the console; windowed bundles are started without one"""
    if sys.stdout is not None:
        print(message)
    return 0


def main(argv=None):
    """Start the interface, queueing every URL given on the command line"""
    argv = list(sys.argv[1:] if argv is None else argv)
    if {'-h', '--help'}.intersection(argv):
        return report(USAGE)
    if {'-v', '--version'}.intersection(argv):
        return report(__version__)

    unknown = next((arg for arg in argv if arg.startswith('-')), None)
    if unknown:
        sys.exit(f'ERROR: unknown option {unknown}\n{USAGE}')

    try:
        import tkinter  # noqa: F401
    except ImportError:
        sys.exit(MISSING_TKINTER)

    from .app import YtDlpGUI
    return YtDlpGUI(argv).run()
