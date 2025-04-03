#!/usr/bin/env python3

# Execute with
# $ python3 -m yt_dlp

import sys
from pathlib import Path

if __package__ is None and not getattr(sys, 'frozen', False):
    # direct call of __main__.py
    path = Path(__file__).resolve()
    sys.path.insert(0, str(path.parent.parent))

import yt_dlp

if __name__ == '__main__':

    yt_dlp.main()
