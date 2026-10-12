from .hls import HlsFD


class TwitterSpacesFD(HlsFD):
    FD_NAME = 'twitterspaces'

    def _read_fragment(self, ctx):
        frag_content = super()._read_fragment(ctx)
        idx = frag_content.find(bytes(
            [0x49, 0x44, 0x33, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x50, 0x52, 0x49, 0x56]))
        if idx > 0:
            # self.to_screen(f'[{self.FD_NAME}] Removing partial header ({idx} bytes)')
            return frag_content[idx:]
        else:
            return frag_content
