import dataclasses
import enum
import io


class UMPPartId(enum.IntEnum):
    ONESIE_HEADER = 10
    ONESIE_DATA = 11
    ONESIE_ENCRYPTED_MEDIA = 12
    MEDIA_HEADER = 20
    MEDIA = 21
    MEDIA_END = 22
    LIVE_METADATA = 31
    HOSTNAME_CHANGE_HINT = 32
    LIVE_METADATA_PROMISE = 33
    LIVE_METADATA_PROMISE_CANCELLATION = 34
    NEXT_REQUEST_POLICY = 35
    USTREAMER_VIDEO_AND_FORMAT_DATA = 36
    FORMAT_SELECTION_CONFIG = 37
    USTREAMER_SELECTED_MEDIA_STREAM = 38
    FORMAT_INITIALIZATION_METADATA = 42
    SABR_REDIRECT = 43
    SABR_ERROR = 44
    SABR_SEEK = 45
    RELOAD_PLAYER_RESPONSE = 46
    PLAYBACK_START_POLICY = 47
    ALLOWED_CACHED_FORMATS = 48
    START_BW_SAMPLING_HINT = 49
    PAUSE_BW_SAMPLING_HINT = 50
    SELECTABLE_FORMATS = 51
    REQUEST_IDENTIFIER = 52
    REQUEST_CANCELLATION_POLICY = 53
    ONESIE_PREFETCH_REJECTION = 54
    TIMELINE_CONTEXT = 55
    REQUEST_PIPELINING = 56
    SABR_CONTEXT_UPDATE = 57
    STREAM_PROTECTION_STATUS = 58
    SABR_CONTEXT_SENDING_POLICY = 59
    LAWNMOWER_POLICY = 60
    SABR_ACK = 61
    END_OF_TRACK = 62
    CACHE_LOAD_POLICY = 63
    LAWNMOWER_MESSAGING_POLICY = 64
    PREWARM_CONNECTION = 65
    PLAYBACK_DEBUG_INFO = 66
    SNACKBAR_MESSAGE = 67
    NETWORK_TIMING = 68
    CUEPOINT_LIST = 69
    STITCHED_REGIONS_OF_INTEREST = 70
    STITCHED_SEGMENTS_METADATA_LIST = 71
    PROBE_SUCCESS = 72

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, int):
            raise ValueError(f'{value!r} is not a valid {cls.__name__}')
        # Do not error on unknown values; create a fake member
        new_member = int.__new__(cls, value)
        new_member._name_ = f'UNKNOWN_{value}'
        new_member._value_ = value
        return new_member


@dataclasses.dataclass
class UMPPart:
    part_id: UMPPartId
    size: int
    data: io.BufferedIOBase


class UMPPartStream(io.BufferedIOBase):
    """
    Wrapper around UMP decoder response file that limits the reader to a window covering only the part.
    """

    def __init__(self, fp: io.BufferedIOBase, size: int):
        self._fp = fp
        self._remaining = size
        self._buffer: io.BytesIO | None = None
        self._consumed = 0

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return False

    def tell(self):
        return self._consumed

    @property
    def remaining(self):
        return self._remaining

    def _read_fp(self, size: int = -1) -> bytes:
        size = self._remaining if size is None or size < 0 else min(size, self._remaining)
        data = self._fp.read(size) or b''
        if len(data) < size:
            raise EOFError(f'Unexpected EOF while reading part data (expected {size}, got {len(data)})')
        return data

    def read(self, size: int = -1):
        if self.closed:
            raise ValueError('I/O operation on closed file')

        if size == 0:
            return b''

        # read from the buffer if drained
        if self._buffer is not None:
            data = self._buffer.read(size)
            self._consumed += len(data)
            return data

        if self._remaining <= 0:
            return b''

        data = self._read_fp(size)
        self._remaining -= len(data)
        self._consumed += len(data)
        if not data:
            self._remaining = 0
        return data

    def drain(self):
        # read the rest of the remaining part data into memory
        # so underlying file points to the next part
        if self.closed:
            raise ValueError('I/O operation on closed file')
        if self._remaining <= 0:
            return
        data = self._read_fp()
        self._remaining = 0
        self._buffer = io.BytesIO(data)

    def discard(self):
        if self.closed:
            raise ValueError('I/O operation on closed file')
        if self._remaining <= 0:
            return
        while self._remaining > 0:
            chunk_size = min(self._remaining, io.DEFAULT_BUFFER_SIZE)
            data = self._read_fp(chunk_size)
            if not data:
                break
            self._remaining -= len(data)
            self._consumed += len(data)

    def close(self):
        self._buffer = None
        super().close()


class UMPDecoder:
    def __init__(self, fp: io.BufferedIOBase):
        self.fp = fp

    def iter_parts(self):
        while not self.fp.closed:
            part_type = read_varint(self.fp)
            if part_type == -1 and not self.fp.closed:
                self.fp.close()

            if self.fp.closed:
                break
            part_size = read_varint(self.fp)
            if part_size == -1 and not self.fp.closed:
                self.fp.close()

            if self.fp.closed:
                raise EOFError('Unexpected EOF while reading part size')

            part_stream = UMPPartStream(self.fp, part_size)
            yield UMPPart(UMPPartId(part_type), part_size, part_stream)

            # Allow part stream to be read at a later time,
            # after we have already moved onto the next part.
            if not part_stream.closed:
                part_stream.drain()
            else:
                # Ensure decoder is aligned to next part.
                # This is for the case the part stream was closed without draining
                if part_stream.remaining > 0:
                    drain_stream = UMPPartStream(self.fp, part_stream.remaining)
                    drain_stream.discard()
                    drain_stream.close()


class UMPEncoder:
    def __init__(self, fp: io.BufferedIOBase):
        self.fp = fp

    def write_part(self, part: UMPPart) -> None:
        write_varint(self.fp, part.part_id.value)
        write_varint(self.fp, part.size)
        self.fp.write(part.data.read())

    __enter__ = lambda self: self
    __exit__ = lambda self, exc_type, exc_value, traceback: None


def read_varint(fp: io.BufferedIOBase) -> int:
    # https://web.archive.org/web/20250430054327/https://github.com/gsuberland/UMP_Format/blob/main/UMP_Format.md
    # https://web.archive.org/web/20250429151021/https://github.com/davidzeng0/innertube/blob/main/googlevideo/ump.md
    byte = fp.read(1)
    if not byte:
        # Expected EOF
        return -1

    prefix = byte[0]
    size = varint_size(prefix)
    result = 0
    shift = 0

    if size != 5:
        shift = 8 - size
        mask = (1 << shift) - 1
        result |= prefix & mask

    for _ in range(1, size):
        next_byte = fp.read(1)
        if not next_byte:
            return -1
        byte_int = next_byte[0]
        result |= byte_int << shift
        shift += 8

    return result


def varint_size(byte: int) -> int:
    return 1 if byte < 128 else 2 if byte < 192 else 3 if byte < 224 else 4 if byte < 240 else 5


def write_varint(fp: io.BufferedIOBase, value: int) -> None:
    # ref: https://github.com/LuanRT/googlevideo/blob/main/src/core/UmpWriter.ts
    if value < 0:
        raise ValueError('Value must be a non-negative integer')

    if value < 128:
        fp.write(bytes([value]))
    elif value < 16384:
        fp.write(bytes([
            (value & 0x3F) | 0x80,
            value >> 6,
        ]))
    elif value < 2097152:
        fp.write(bytes([
            (value & 0x1F) | 0xC0,
            (value >> 5) & 0xFF,
            value >> 13,
        ]))
    elif value < 268435456:
        fp.write(bytes([
            (value & 0x0F) | 0xE0,
            (value >> 4) & 0xFF,
            (value >> 12) & 0xFF,
            value >> 20,
        ]))
    else:
        data = bytearray(5)
        data[0] = 0xF0
        data[1:5] = value.to_bytes(4, 'little')
        fp.write(data)
