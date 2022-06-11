import struct

from typing import Tuple
from io import BytesIO, RawIOBase


class LengthLimiter(RawIOBase):
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
    return struct.pack('>I', value)


def pack_be64(value: int) -> bytes:
    return struct.pack('>L', value)


def unpack_be32(value: bytes) -> int:
    return struct.unpack('>I', value)[0]


def unpack_ver_flags(value: bytes) -> Tuple[int, int]:
    ver, up_flag, down_flag = struct.unpack('>BBH', value)
    return ver, (up_flag << 16 | down_flag)


def unpack_be64(value: bytes) -> int:
    return struct.unpack('>L', value)[0]


# https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L13-L40
MP4_CONTAINER_BOXES = ('moov', 'trak', 'edts', 'mdia', 'minf', 'dinf', 'stbl', 'mvex', 'moof', 'traf', 'vttc', 'tref', 'iref', 'mfra', 'meco', 'hnti', 'hinf', 'strk', 'strd', 'sinf', 'rinf', 'schi', 'trgr', 'udta', 'iprp', 'ipco')


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
    ('box1', b'')       /box1           (start of container box)
    ('helo', b'abcdef') /box1/helo
    ('1984', b'1q84')   /box1/1984
    ('http', b'')       /box1/http      (start of container box)
    ('keys', b'2022')   /box1/http/keys
    (None  , 'http')    /box1/http      (end of container box)
    ('topp', b'1991')   /box1/topp
    (None  , 'box1')    /box1           (end of container box)
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
