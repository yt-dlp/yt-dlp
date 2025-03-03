import os
import struct

from io import BytesIO, RawIOBase
from math import inf
from typing import Tuple

from .common import PostProcessor
from ..utils import prepend_extension


class LengthLimiter(RawIOBase):
    """
    A bytes IO to limit length to be read.
    """

    def __init__(self, r: RawIOBase, size: int):
        self.r = r
        self.remaining = size

    def read(self, sz: int = None) -> bytes:
        if self.remaining == 0:
            return b''
        if sz in (-1, None):
            sz = self.remaining
        sz = min(sz, self.remaining)
        ret = self.r.read(sz)
        if ret:
            self.remaining -= len(ret)
        return ret

    def readall(self) -> bytes:
        if self.remaining == 0:
            return b''
        ret = self.read(self.remaining)
        if ret:
            self.remaining -= len(ret)
        return ret

    def readable(self) -> bool:
        return bool(self.remaining)


def read_harder(r, size):
    """
    Try to read from the stream.

    @params r    byte stream to read
    @params size Number of bytes to read in total
    """

    retry = 0
    buf = b''
    while len(buf) < size and retry < 3:
        ret = r.read(size - len(buf))
        if not ret:
            retry += 1
            continue
        retry = 0
        buf += ret

    return buf


def pack_be32(value: int) -> bytes:
    """ Pack value to 4-byte-long bytes in the big-endian byte order """
    return struct.pack('>I', value)


def pack_be64(value: int) -> bytes:
    """ Pack value to 8-byte-long bytes in the big-endian byte order """
    return struct.pack('>L', value)


def unpack_be32(value: bytes) -> int:
    """ Convert 4-byte-long bytes in the big-endian byte order, to an integer value """
    return struct.unpack('>I', value)[0]


def unpack_be64(value: bytes) -> int:
    """ Convert 8-byte-long bytes in the big-endian byte order, to an integer value """
    return struct.unpack('>L', value)[0]


def unpack_ver_flags(value: bytes) -> Tuple[int, int]:
    """
    Unpack 4-byte-long value into version and flags.
    @returns (version, flags)
    """

    ver, up_flag, down_flag = struct.unpack('>BBH', value)
    return ver, (up_flag << 16 | down_flag)


# https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L13-L40
MP4_CONTAINER_BOXES = ('moov', 'trak', 'edts', 'mdia', 'minf', 'dinf', 'stbl', 'mvex', 'moof', 'traf', 'vttc', 'tref', 'iref', 'mfra', 'meco', 'hnti', 'hinf', 'strk', 'strd', 'sinf', 'rinf', 'schi', 'trgr', 'udta', 'iprp', 'ipco')
""" List of boxes that nests the other boxes """


def parse_mp4_boxes(r: RawIOBase):
    """
    Parses an ISO BMFF (which MP4 follows) and yields its boxes as a sequence.
    This does not interpret content of these boxes.

    Sequence details:
    ('atom', b'blablabla'): A box, with content (not container boxes)
    ('atom', b''):          Possibly container box (must check MP4_CONTAINER_BOXES) or really an empty box
    (None, 'atom'):         End of a container box

    Example:            Path:
    ('test', b'123456') /test
    ('moov', b'')       /moov           (start of container box)
    ('helo', b'abcdef') /moov/helo
    ('1984', b'1q84')   /moov/1984
    ('trak', b'')       /moov/trak      (start of container box)
    ('keys', b'2022')   /moov/trak/keys
    (None  , 'trak')    /moov/trak      (end of container box)
    ('topp', b'1991')   /moov/topp
    (None  , 'moov')    /moov           (end of container box)
    """

    while True:
        size_b = read_harder(r, 4)
        if not size_b:
            break
        type_b = r.read(4)
        # 00 00 00 20 is big-endian
        box_size = unpack_be32(size_b)
        type_s = type_b.decode()
        if type_s in MP4_CONTAINER_BOXES:
            yield (type_s, b'')
            yield from parse_mp4_boxes(LengthLimiter(r, box_size - 8))
            yield (None, type_s)
            continue
        # subtract by 8
        full_body = read_harder(r, box_size - 8)
        yield (type_s, full_body)


def write_mp4_boxes(w: RawIOBase, box_iter):
    """
    Writes an ISO BMFF file from a given sequence to a given writer.
    The iterator to be passed must follow parse_mp4_boxes's protocol.
    """

    stack = [
        (None, w),  # parent box, IO
    ]
    for btype, content in box_iter:
        if btype in MP4_CONTAINER_BOXES:
            bio = BytesIO()
            stack.append((btype, bio))
            continue
        elif btype is None:
            assert stack[-1][0] == content
            btype, bio = stack.pop()
            content = bio.getvalue()

        wt = stack[-1][1]
        wt.write(pack_be32(len(content) + 8))
        wt.write(btype.encode()[:4])
        wt.write(content)


class MP4FixupTimestampPP(PostProcessor):

    @property
    def available(self):
        return True

    def analyze_mp4(self, filepath):
        """ returns (baseMediaDecodeTime offset, sample duration cutoff) """
        smallest_bmdt, known_sdur = inf, set()
        with open(filepath, 'rb') as r:
            for btype, content in parse_mp4_boxes(r):
                if btype == 'tfdt':
                    version, _ = unpack_ver_flags(content[0:4])
                    # baseMediaDecodeTime always comes to the first
                    if version == 0:
                        bmdt = unpack_be32(content[4:8])
                    else:
                        bmdt = unpack_be64(content[4:12])
                    if bmdt == 0:
                        continue
                    smallest_bmdt = min(bmdt, smallest_bmdt)
                elif btype == 'tfhd':
                    version, flags = unpack_ver_flags(content[0:4])
                    if not flags & 0x08:
                        # this box does not contain "sample duration"
                        continue
                    # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L203-L209
                    # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/parsing/tfhd.js
                    sdur_start = 8  # header + track id
                    if flags & 0x01:
                        sdur_start += 8
                    if flags & 0x02:
                        sdur_start += 4
                    # the next 4 bytes are "sample duration"
                    sample_dur = unpack_be32(content[sdur_start:sdur_start + 4])
                    known_sdur.add(sample_dur)

        maximum_sdur = max(known_sdur)
        for multiplier in (0.7, 0.8, 0.9, 0.95):
            sdur_cutoff = maximum_sdur * multiplier
            if len(set(x for x in known_sdur if x > sdur_cutoff)) < 3:
                break
        else:
            sdur_cutoff = inf

        return smallest_bmdt, sdur_cutoff

    @staticmethod
    def transform(r, bmdt_offset, sdur_cutoff):
        for btype, content in r:
            if btype == 'tfdt':
                version, _ = unpack_ver_flags(content[0:4])
                if version == 0:
                    bmdt = unpack_be32(content[4:8])
                else:
                    bmdt = unpack_be64(content[4:12])
                if bmdt == 0:
                    yield (btype, content)
                    continue
                # calculate new baseMediaDecodeTime
                bmdt = max(0, bmdt - bmdt_offset)
                # pack everything again and insert as a new box
                if version == 0:
                    bmdt_b = pack_be32(bmdt)
                else:
                    bmdt_b = pack_be64(bmdt)
                yield ('tfdt', content[0:4] + bmdt_b + content[8 + version * 4:])
                continue
            elif btype == 'tfhd':
                version, flags = unpack_ver_flags(content[0:4])
                if not flags & 0x08:
                    yield (btype, content)
                    continue
                sdur_start = 8
                if flags & 0x01:
                    sdur_start += 8
                if flags & 0x02:
                    sdur_start += 4
                sample_dur = unpack_be32(content[sdur_start:sdur_start + 4])
                if sample_dur > sdur_cutoff:
                    sample_dur = 0
                sd_b = pack_be32(sample_dur)
                yield ('tfhd', content[:sdur_start] + sd_b + content[sdur_start + 4:])
                continue
            yield (btype, content)

    def modify_mp4(self, src, dst, bmdt_offset, sdur_cutoff):
        with open(src, 'rb') as r, open(dst, 'wb') as w:
            write_mp4_boxes(w, self.transform(parse_mp4_boxes(r)))

    def run(self, information):
        filename = information['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        self.write_debug('Analyzing MP4')
        bmdt_offset, sdur_cutoff = self.analyze_mp4(filename)
        working = inf not in (bmdt_offset, sdur_cutoff)
        # if any of them are Infinity, there's something wrong
        # baseMediaDecodeTime = to shift PTS
        # sample duration = to define duration in each segment
        self.write_debug(f'baseMediaDecodeTime offset = {bmdt_offset}, sample duration cutoff = {sdur_cutoff}')
        if bmdt_offset == inf:
            # safeguard
            bmdt_offset = 0
        self.modify_mp4(filename, temp_filename, bmdt_offset, sdur_cutoff)
        if working:
            self.to_screen('Duration of the file has been fixed')
        else:
            self.report_warning(f'Failed to fix duration of the file. (baseMediaDecodeTime offset = {bmdt_offset}, sample duration cutoff = {sdur_cutoff})')

        os.replace(temp_filename, filename)

        return [], information
