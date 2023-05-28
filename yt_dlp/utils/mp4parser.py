import enum
import io
import re

from ..downloader.ism import extract_box_data

GF_ISOM_TRUN_DATA_OFFSET = 0x01
GF_ISOM_TRUN_FIRST_FLAG = 0x04
GF_ISOM_TRUN_DURATION = 0x100
GF_ISOM_TRUN_SIZE = 0x200
GF_ISOM_TRUN_FLAGS = 0x400
GF_ISOM_TRUN_CTS_OFFSET = 0x800


class SubtitleType(enum.Enum):
    SUBS_XML = enum.auto()
    WEBVTT = enum.auto()
    SIMPLE_TEXT = enum.auto()
    SUBS_TEXT = enum.auto()
    TX3G = enum.auto()
    SUBPIC = enum.auto()


def prepare(mp4_data):
    stype, mdat, trun = None, [], []
    selection = {b'ftyp', b'moov', b'moof', b'mdat'}
    for box_type, box_data in extract_box_data(mp4_data, selection):
        if box_type == b'moov':
            if re.search(b'stbl.+stsd.+stpp', box_data):
                stype = SubtitleType.SUBS_XML
            if re.search(b'stbl.+stsd.+wvtt', box_data):
                stype = SubtitleType.WEBVTT
            # TODO stxt:SIMPLE_TEXT, sbtt:SUBS_TEXT, tx3g:TX3G, SUBPIC
            continue
        if box_type == b'mdat':
            mdat.append(box_data)
        if stype == SubtitleType.WEBVTT:
            if box_type == b'moof':
                pos = box_data.find(b'trun')
                tail = box_data[pos + 4:]
                trun.append(tail)

    if stype == SubtitleType.SUBS_XML:
        return stype, mdat
    elif stype == SubtitleType.WEBVTT:
        return stype, zip(trun, mdat)


def read_trun(trun):
    # https://github.com/gpac/gpac/blob/62a4ad6b5cd088834a2f1853db227397edda8cbe/src/isomedia/box_code_base.c#L7562-L7648
    data_reader = io.BytesIO(trun)

    def read32():
        b = data_reader.read(4)
        return int.from_bytes(b, 'big')

    flags = read32()
    if flags & GF_ISOM_TRUN_FIRST_FLAG and flags & GF_ISOM_TRUN_FLAGS:
        raise ValueError('INVALID_FILE')

    sample_count = read32()
    if flags & GF_ISOM_TRUN_DATA_OFFSET:
        _ = read32()

    if flags & GF_ISOM_TRUN_FIRST_FLAG:
        _ = read32()

    samples = [{'id': x} for x in range(sample_count)]

    for p in samples:

        if flags & GF_ISOM_TRUN_DURATION:
            p['Duration'] = read32()
        else:
            p['Duration'] = 0

        if flags & GF_ISOM_TRUN_SIZE:
            p['size'] = read32()
        else:
            p['size'] = 0

        if flags & GF_ISOM_TRUN_FLAGS:
            p['flags'] = read32()
        else:
            p['flags'] = 0

        if flags & GF_ISOM_TRUN_CTS_OFFSET:
            p['CTS_Offset'] = read32()
        else:
            p['CTS_Offset'] = 0

    return samples


def _time2txt(t):
    # https://github.com/gpac/gpac/blob/2ce645d23c88a3f776d92783549085380903608c/src/media_tools/webvtt.c#L1368-L1395
    sec_, msec = divmod(t, 1000)
    min_, sec_ = divmod(sec_, 60)
    hour, min_ = divmod(min_, 60)
    return f'{hour:02}:{min_:02}:{sec_:02},{msec:03}'


def webvtt2srt(info, data, ts):
    # https://github.com/gpac/gpac/blob/2ce645d23c88a3f776d92783549085380903608c/src/media_tools/webvtt.c#L1197-L1246
    size = info['size']
    start_ts = ts
    end_ts = start_ts + info['Duration']
    head, tail = data[:size], data[size:]
    if b'payl' not in head:
        return None, tail, end_ts

    pos = head.find(b'payl')
    txt = head[pos + 4:].decode('utf-8')

    start_end = f'{_time2txt(start_ts)} --> {_time2txt(end_ts)}'
    lines = f'{start_end}\n{txt}\n'
    return lines, tail, end_ts
