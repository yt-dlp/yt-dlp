import binascii
import io
import struct
import time

from .fragment import FragmentFD
from ..compat import compat_urllib_error

u8 = struct.Struct('>B')
u88 = struct.Struct('>Bx')
u16 = struct.Struct('>H')
u1616 = struct.Struct('>Hxx')
u32 = struct.Struct('>I')
u64 = struct.Struct('>Q')

s88 = struct.Struct('>bx')
s16 = struct.Struct('>h')
s1616 = struct.Struct('>hxx')
s32 = struct.Struct('>i')

unity_matrix = (s32.pack(0x10000) + s32.pack(0) * 3) * 2 + s32.pack(0x40000000)

TRACK_ENABLED = 0x1
TRACK_IN_MOVIE = 0x2
TRACK_IN_PREVIEW = 0x4

SELF_CONTAINED = 0x1


def box(box_type, payload):
    return u32.pack(8 + len(payload)) + box_type + payload


def full_box(box_type, version, flags, payload):
    return box(box_type, u8.pack(version) + u32.pack(flags)[1:] + payload)


def write_piff_header(stream, params):
    track_id = params['track_id']
    fourcc = params['fourcc']
    duration = params['duration']
    timescale = params.get('timescale', 10000000)
    language = params.get('language', 'und')
    height = params.get('height', 0)
    width = params.get('width', 0)
    stream_type = params['stream_type']
    creation_time = modification_time = int(time.time())

    ftyp_payload = b'isml'  # major brand
    ftyp_payload += u32.pack(1)  # minor version
    ftyp_payload += b'piff' + b'iso2'  # compatible brands
    stream.write(box(b'ftyp', ftyp_payload))  # File Type Box

    mvhd_payload = u64.pack(creation_time)
    mvhd_payload += u64.pack(modification_time)
    mvhd_payload += u32.pack(timescale)
    mvhd_payload += u64.pack(duration)
    mvhd_payload += s1616.pack(1)  # rate
    mvhd_payload += s88.pack(1)  # volume
    mvhd_payload += u16.pack(0)  # reserved
    mvhd_payload += u32.pack(0) * 2  # reserved
    mvhd_payload += unity_matrix
    mvhd_payload += u32.pack(0) * 6  # pre defined
    mvhd_payload += u32.pack(0xffffffff)  # next track id
    moov_payload = full_box(b'mvhd', 1, 0, mvhd_payload)  # Movie Header Box

    tkhd_payload = u64.pack(creation_time)
    tkhd_payload += u64.pack(modification_time)
    tkhd_payload += u32.pack(track_id)  # track id
    tkhd_payload += u32.pack(0)  # reserved
    tkhd_payload += u64.pack(duration)
    tkhd_payload += u32.pack(0) * 2  # reserved
    tkhd_payload += s16.pack(0)  # layer
    tkhd_payload += s16.pack(0)  # alternate group
    tkhd_payload += s88.pack(1 if stream_type == 'audio' else 0)  # volume
    tkhd_payload += u16.pack(0)  # reserved
    tkhd_payload += unity_matrix
    tkhd_payload += u1616.pack(width)
    tkhd_payload += u1616.pack(height)
    trak_payload = full_box(b'tkhd', 1, TRACK_ENABLED | TRACK_IN_MOVIE | TRACK_IN_PREVIEW, tkhd_payload)  # Track Header Box

    mdhd_payload = u64.pack(creation_time)
    mdhd_payload += u64.pack(modification_time)
    mdhd_payload += u32.pack(timescale)
    mdhd_payload += u64.pack(duration)
    mdhd_payload += u16.pack(((ord(language[0]) - 0x60) << 10) | ((ord(language[1]) - 0x60) << 5) | (ord(language[2]) - 0x60))
    mdhd_payload += u16.pack(0)  # pre defined
    mdia_payload = full_box(b'mdhd', 1, 0, mdhd_payload)  # Media Header Box

    hdlr_payload = u32.pack(0)  # pre defined
    if stream_type == 'audio':  # handler type
        hdlr_payload += b'soun'
        hdlr_payload += u32.pack(0) * 3  # reserved
        hdlr_payload += b'SoundHandler\0'  # name
    elif stream_type == 'video':
        hdlr_payload += b'vide'
        hdlr_payload += u32.pack(0) * 3  # reserved
        hdlr_payload += b'VideoHandler\0'  # name
    elif stream_type == 'text':
        hdlr_payload += b'subt'
        hdlr_payload += u32.pack(0) * 3  # reserved
        hdlr_payload += b'SubtitleHandler\0'  # name
    else:
        assert False
    mdia_payload += full_box(b'hdlr', 0, 0, hdlr_payload)  # Handler Reference Box

    if stream_type == 'audio':
        smhd_payload = s88.pack(0)  # balance
        smhd_payload += u16.pack(0)  # reserved
        media_header_box = full_box(b'smhd', 0, 0, smhd_payload)  # Sound Media Header
    elif stream_type == 'video':
        vmhd_payload = u16.pack(0)  # graphics mode
        vmhd_payload += u16.pack(0) * 3  # opcolor
        media_header_box = full_box(b'vmhd', 0, 1, vmhd_payload)  # Video Media Header
    elif stream_type == 'text':
        media_header_box = full_box(b'sthd', 0, 0, b'')  # Subtitle Media Header
    else:
        assert False
    minf_payload = media_header_box

    dref_payload = u32.pack(1)  # entry count
    dref_payload += full_box(b'url ', 0, SELF_CONTAINED, b'')  # Data Entry URL Box
    dinf_payload = full_box(b'dref', 0, 0, dref_payload)  # Data Reference Box
    minf_payload += box(b'dinf', dinf_payload)  # Data Information Box

    stsd_payload = u32.pack(1)  # entry count

    sample_entry_payload = u8.pack(0) * 6  # reserved
    sample_entry_payload += u16.pack(1)  # data reference index
    if stream_type == 'audio':
        sample_entry_payload += u32.pack(0) * 2  # reserved
        sample_entry_payload += u16.pack(params.get('channels', 2))
        sample_entry_payload += u16.pack(params.get('bits_per_sample', 16))
        sample_entry_payload += u16.pack(0)  # pre defined
        sample_entry_payload += u16.pack(0)  # reserved
        sample_entry_payload += u1616.pack(params['sampling_rate'])

        if fourcc == 'AACL':
            sample_entry_box = box(b'mp4a', sample_entry_payload)
    elif stream_type == 'video':
        sample_entry_payload += u16.pack(0)  # pre defined
        sample_entry_payload += u16.pack(0)  # reserved
        sample_entry_payload += u32.pack(0) * 3  # pre defined
        sample_entry_payload += u16.pack(width)
        sample_entry_payload += u16.pack(height)
        sample_entry_payload += u1616.pack(0x48)  # horiz resolution 72 dpi
        sample_entry_payload += u1616.pack(0x48)  # vert resolution 72 dpi
        sample_entry_payload += u32.pack(0)  # reserved
        sample_entry_payload += u16.pack(1)  # frame count
        sample_entry_payload += u8.pack(0) * 32  # compressor name
        sample_entry_payload += u16.pack(0x18)  # depth
        sample_entry_payload += s16.pack(-1)  # pre defined

        codec_private_data = binascii.unhexlify(params['codec_private_data'].encode())
        if fourcc in ('H264', 'AVC1'):
            sps, pps = codec_private_data.split(u32.pack(1))[1:]
            avcc_payload = u8.pack(1)  # configuration version
            avcc_payload += sps[1:4]  # avc profile indication + profile compatibility + avc level indication
            avcc_payload += u8.pack(0xfc | (params.get('nal_unit_length_field', 4) - 1))  # complete representation (1) + reserved (11111) + length size minus one
            avcc_payload += u8.pack(1)  # reserved (0) + number of sps (0000001)
            avcc_payload += u16.pack(len(sps))
            avcc_payload += sps
            avcc_payload += u8.pack(1)  # number of pps
            avcc_payload += u16.pack(len(pps))
            avcc_payload += pps
            sample_entry_payload += box(b'avcC', avcc_payload)  # AVC Decoder Configuration Record
            sample_entry_box = box(b'avc1', sample_entry_payload)  # AVC Simple Entry
        else:
            assert False
    elif stream_type == 'text':
        if fourcc == 'TTML':
            sample_entry_payload += b'http://www.w3.org/ns/ttml\0'  # namespace
            sample_entry_payload += b'\0'  # schema location
            sample_entry_payload += b'\0'  # auxilary mime types(??)
            sample_entry_box = box(b'stpp', sample_entry_payload)
        else:
            assert False
    else:
        assert False
    stsd_payload += sample_entry_box

    stbl_payload = full_box(b'stsd', 0, 0, stsd_payload)  # Sample Description Box

    stts_payload = u32.pack(0)  # entry count
    stbl_payload += full_box(b'stts', 0, 0, stts_payload)  # Decoding Time to Sample Box

    stsc_payload = u32.pack(0)  # entry count
    stbl_payload += full_box(b'stsc', 0, 0, stsc_payload)  # Sample To Chunk Box

    stco_payload = u32.pack(0)  # entry count
    stbl_payload += full_box(b'stco', 0, 0, stco_payload)  # Chunk Offset Box

    minf_payload += box(b'stbl', stbl_payload)  # Sample Table Box

    mdia_payload += box(b'minf', minf_payload)  # Media Information Box

    trak_payload += box(b'mdia', mdia_payload)  # Media Box

    moov_payload += box(b'trak', trak_payload)  # Track Box

    mehd_payload = u64.pack(duration)
    mvex_payload = full_box(b'mehd', 1, 0, mehd_payload)  # Movie Extends Header Box

    trex_payload = u32.pack(track_id)  # track id
    trex_payload += u32.pack(1)  # default sample description index
    trex_payload += u32.pack(0)  # default sample duration
    trex_payload += u32.pack(0)  # default sample size
    trex_payload += u32.pack(0)  # default sample flags
    mvex_payload += full_box(b'trex', 0, 0, trex_payload)  # Track Extends Box

    moov_payload += box(b'mvex', mvex_payload)  # Movie Extends Box
    stream.write(box(b'moov', moov_payload))  # Movie Box


def extract_box_data(data, box_sequence):
    data_reader = io.BytesIO(data)
    while True:
        box_size = u32.unpack(data_reader.read(4))[0]
        box_type = data_reader.read(4)
        if box_type == box_sequence[0]:
            box_data = data_reader.read(box_size - 8)
            if len(box_sequence) == 1:
                return box_data
            return extract_box_data(box_data, box_sequence[1:])
        data_reader.seek(box_size - 8, 1)


class IsmFD(FragmentFD):
    """
    Download segments in a ISM manifest
    """

    def real_download(self, filename, info_dict):
        segments = info_dict['fragments'][:1] if self.params.get(
            'test', False) else info_dict['fragments']

        ctx = {
            'filename': filename,
            'total_frags': len(segments),
        }

        self._prepare_and_start_frag_download(ctx, info_dict)

        extra_state = ctx.setdefault('extra_state', {
            'ism_track_written': False,
        })

        fragment_retries = self.params.get('fragment_retries', 0)
        skip_unavailable_fragments = self.params.get('skip_unavailable_fragments', True)

        frag_index = 0
        for i, segment in enumerate(segments):
            frag_index += 1
            if frag_index <= ctx['fragment_index']:
                continue
            count = 0
            while count <= fragment_retries:
                try:
                    success = self._download_fragment(ctx, segment['url'], info_dict)
                    if not success:
                        return False
                    frag_content = self._read_fragment(ctx)

                    if not extra_state['ism_track_written']:
                        tfhd_data = extract_box_data(frag_content, [b'moof', b'traf', b'tfhd'])
                        info_dict['_download_params']['track_id'] = u32.unpack(tfhd_data[4:8])[0]
                        write_piff_header(ctx['dest_stream'], info_dict['_download_params'])
                        extra_state['ism_track_written'] = True
                    self._append_fragment(ctx, frag_content)
                    break
                except compat_urllib_error.HTTPError as err:
                    count += 1
                    if count <= fragment_retries:
                        self.report_retry_fragment(err, frag_index, count, fragment_retries)
            if count > fragment_retries:
                if skip_unavailable_fragments:
                    self.report_skip_fragment(frag_index)
                    continue
                self.report_error('giving up after %s fragment retries' % fragment_retries)
                return False

        self._finish_frag_download(ctx, info_dict)

        return True
