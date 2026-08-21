#!/usr/bin/env python3

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import subprocess

from PIL import Image

SOURCE = 'devscripts/logo.ico'

ICONSET_ENTRIES = (
    ('icon_16x16.png', 16),
    ('icon_16x16@2x.png', 32),
    ('icon_32x32.png', 32),
    ('icon_32x32@2x.png', 64),
    ('icon_128x128.png', 128),
    ('icon_128x128@2x.png', 256),
    ('icon_256x256.png', 256),
    ('icon_256x256@2x.png', 512),
    ('icon_512x512.png', 512),
    ('icon_512x512@2x.png', 1024),
)


def load_logo(source=SOURCE):
    """@returns the largest frame of the icon file as RGBA"""
    with Image.open(source) as icon:
        return icon.convert('RGBA')


def write_png(dest, size=256, source=SOURCE):
    """Write a single square PNG, never upscaling beyond the source"""
    logo = load_logo(source)
    size = min(size, logo.width)
    make_parent_dir(dest)
    logo.resize((size, size), Image.LANCZOS).save(dest, 'PNG')
    return dest


def write_icns(dest, source=SOURCE):
    """Write an Apple icon suite, which is the only format PyInstaller accepts on macOS"""
    logo = load_logo(source)
    iconset = f'{os.path.splitext(dest)[0]}.iconset'
    os.makedirs(iconset, exist_ok=True)
    for name, size in ICONSET_ENTRIES:
        if size > logo.width:
            continue
        logo.resize((size, size), Image.LANCZOS).save(os.path.join(iconset, name), 'PNG')

    make_parent_dir(dest)
    subprocess.run(['iconutil', '--convert', 'icns', iconset, '--output', dest], check=True)
    return dest


def make_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Convert the yt-dlp logo into GUI icon formats')
    parser.add_argument('--source', default=SOURCE, help=f'icon to convert (default: {SOURCE})')
    parser.add_argument('--png', metavar='PATH', help='write a PNG for the Linux desktop entry')
    parser.add_argument('--size', type=int, default=256, help='size of the PNG (default: 256)')
    parser.add_argument('--icns', metavar='PATH', help='write an icns for the macOS bundle')
    args = parser.parse_args()

    if not args.png and not args.icns:
        parser.error('nothing to do: pass --png and/or --icns')
    if args.png:
        print(f'Wrote {write_png(args.png, args.size, args.source)}')
    if args.icns:
        print(f'Wrote {write_icns(args.icns, args.source)}')


if __name__ == '__main__':
    main()
