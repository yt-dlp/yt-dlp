"""No longer used and new code should not use. Exists only for API compat."""

import platform
import struct
import sys
import urllib.parse
import zlib

from ._utils import Popen, decode_base_n, preferredencoding
from .traversal import traverse_obj
from ..dependencies import certifi, websockets

# isort: split
from ..cookies import YoutubeDLCookieJar  # noqa: F401

has_certifi = bool(certifi)
has_websockets = bool(websockets)


def load_plugins(name, suffix, namespace):
    from ..plugins import load_plugins
    ret = load_plugins(name, suffix)
    namespace.update(ret)
    return ret


def traverse_dict(dictn, keys, casesense=True):
    return traverse_obj(dictn, keys, casesense=casesense, is_user_input=True, traverse_string=True)


def decode_base(value, digits):
    return decode_base_n(value, table=digits)


def platform_name():
    """ Returns the platform name as a str """
    return platform.platform()


def get_subprocess_encoding():
    if sys.platform == 'win32' and sys.getwindowsversion()[0] >= 5:
        # For subprocess calls, encode with locale encoding
        # Refer to http://stackoverflow.com/a/9951851/35070
        encoding = preferredencoding()
    else:
        encoding = sys.getfilesystemencoding()
    if encoding is None:
        encoding = 'utf-8'
    return encoding


# UNUSED
# Based on png2str() written by @gdkchan and improved by @yokrysty
# Originally posted at https://github.com/ytdl-org/youtube-dl/issues/9706
def decode_png(png_data):
    # Reference: https://www.w3.org/TR/PNG/
    header = png_data[8:]

    if png_data[:8] != b'\x89PNG\x0d\x0a\x1a\x0a' or header[4:8] != b'IHDR':
        raise OSError('Not a valid PNG file.')

    int_map = {1: '>B', 2: '>H', 4: '>I'}
    unpack_integer = lambda x: struct.unpack(int_map[len(x)], x)[0]

    chunks = []

    while header:
        length = unpack_integer(header[:4])
        header = header[4:]

        chunk_type = header[:4]
        header = header[4:]

        chunk_data = header[:length]
        header = header[length:]

        header = header[4:]  # Skip CRC

        chunks.append({
            'type': chunk_type,
            'length': length,
            'data': chunk_data
        })

    ihdr = chunks[0]['data']

    width = unpack_integer(ihdr[:4])
    height = unpack_integer(ihdr[4:8])

    idat = b''

    for chunk in chunks:
        if chunk['type'] == b'IDAT':
            idat += chunk['data']

    if not idat:
        raise OSError('Unable to read PNG data.')

    decompressed_data = bytearray(zlib.decompress(idat))

    stride = width * 3
    pixels = []

    def _get_pixel(idx):
        x = idx % stride
        y = idx // stride
        return pixels[y][x]

    for y in range(height):
        basePos = y * (1 + stride)
        filter_type = decompressed_data[basePos]

        current_row = []

        pixels.append(current_row)

        for x in range(stride):
            color = decompressed_data[1 + basePos + x]
            basex = y * stride + x
            left = 0
            up = 0

            if x > 2:
                left = _get_pixel(basex - 3)
            if y > 0:
                up = _get_pixel(basex - stride)

            if filter_type == 1:  # Sub
                color = (color + left) & 0xff
            elif filter_type == 2:  # Up
                color = (color + up) & 0xff
            elif filter_type == 3:  # Average
                color = (color + ((left + up) >> 1)) & 0xff
            elif filter_type == 4:  # Paeth
                a = left
                b = up
                c = 0

                if x > 2 and y > 0:
                    c = _get_pixel(basex - stride - 3)

                p = a + b - c

                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)

                if pa <= pb and pa <= pc:
                    color = (color + a) & 0xff
                elif pb <= pc:
                    color = (color + b) & 0xff
                else:
                    color = (color + c) & 0xff

            current_row.append(color)

    return width, height, pixels


def register_socks_protocols():
    # "Register" SOCKS protocols
    # In Python < 2.6.5, urlsplit() suffers from bug https://bugs.python.org/issue7904
    # URLs with protocols not in urlparse.uses_netloc are not handled correctly
    for scheme in ('socks', 'socks4', 'socks4a', 'socks5'):
        if scheme not in urllib.parse.uses_netloc:
            urllib.parse.uses_netloc.append(scheme)


def handle_youtubedl_headers(headers):
    filtered_headers = headers

    if 'Youtubedl-no-compression' in filtered_headers:
        filtered_headers = {k: v for k, v in filtered_headers.items() if k.lower() != 'accept-encoding'}
        del filtered_headers['Youtubedl-no-compression']

    return filtered_headers


def process_communicate_or_kill(p, *args, **kwargs):
    return Popen.communicate_or_kill(p, *args, **kwargs)
