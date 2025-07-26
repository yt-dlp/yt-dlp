import dataclasses
import enum
import io


class UMPPartId(enum.IntEnum):
    UNKNOWN = -1
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

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


@dataclasses.dataclass
class UMPPart:
    part_id: UMPPartId
    size: int
    data: io.BufferedIOBase


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

            part_data = self.fp.read(part_size)
            # In the future, we could allow streaming the part data.
            # But we will need to ensure that each part is completely read before continuing.
            yield UMPPart(UMPPartId(part_type), part_size, io.BytesIO(part_data))


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
