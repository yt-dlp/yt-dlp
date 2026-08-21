#!/usr/bin/env python3

# Execute with
# $ python3 -m yt_dlp.gui

import sys

if __package__ is None and not getattr(sys, 'frozen', False):
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(path))))

import yt_dlp.gui

if __name__ == '__main__':
    sys.exit(yt_dlp.gui.main())
