
from . import HlsFD


class HlsFakeHeaderFD(HlsFD):
    """
    For M3U8 with fake header in each frags
    """

    FD_NAME = 'hlsnative_fake_header'

    def _fixup_fragment(self, ctx, frag_bytes):
        ts_start_pos = frag_bytes.find(b'\x47\x40')
        frag_bytes = frag_bytes[ts_start_pos:]
        return frag_bytes
