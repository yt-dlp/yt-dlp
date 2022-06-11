from math import inf

from .common import PostProcessor
from ..utils import prepend_extension

from ..mp4_parser import (
    write_mp4_boxes,
    parse_mp4_boxes,
    pack_be32,
    pack_be64,
    unpack_ver_flags,
    unpack_be32,
    unpack_be64,
)


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

    def modify_mp4(self, src, dst, bmdt_offset, sdur_cutoff):
        with open(src, 'rb') as r, open(dst, 'wb') as w:
            def converter():
                for btype, content in parse_mp4_boxes(r):
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

            write_mp4_boxes(w, converter())

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

        self._downloader.replace(temp_filename, filename)

        return [], information
