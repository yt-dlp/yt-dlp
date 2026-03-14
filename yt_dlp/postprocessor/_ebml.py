# EBML Element IDs
# RFC 9559 Section 5.1.7 - https://www.rfc-editor.org/rfc/rfc9559#name-chapters-element
# RFC 9559 Section 20    - https://www.rfc-editor.org/rfc/rfc9559#chapters
SEGMENT_ID = 0x18538067
CHAPTERS_ID = 0x1043A770
EDITION_ENTRY_ID = 0x45B9
EDITION_UID_ID = 0x45BC
EDITION_FLAG_DEFAULT_ID = 0x45DB
EDITION_FLAG_ORDERED_ID = 0x45DD
EDITION_DISPLAY_ID = 0x4520
EDITION_STRING_ID = 0x4521
EDITION_LANGUAGE_IETF_ID = 0x45E4
CHAPTER_ATOM_ID = 0xB6
CHAPTER_UID_ID = 0x73C4
CHAPTER_TIME_START_ID = 0x91
CHAPTER_TIME_END_ID = 0x92
CHAPTER_FLAG_HIDDEN_ID = 0x98
CHAPTER_DISPLAY_ID = 0x80
CHAP_STRING_ID = 0x85
CHAP_LANGUAGE_ID = 0x437C


# variable-sized integers
# RFC 8794 Section 4 - https://www.rfc-editor.org/rfc/rfc8794#name-variable-size-integer
_VINT_MASKS = (
    (0x80, 0x7F, 1),
    (0x40, 0x3FFF, 2),
    (0x20, 0x1FFFFF, 3),
    (0x10, 0x0FFFFFFF, 4),
    (0x08, 0x07FFFFFFFF, 5),
    (0x04, 0x03FFFFFFFFFF, 6),
    (0x02, 0x01FFFFFFFFFFFF, 7),
    (0x01, 0x00FFFFFFFFFFFFFF, 8),
)

def read_vint(data, pos):
    if pos >= len(data):
        return None, 0
    first = data[pos]
    for marker, mask, n in _VINT_MASKS:
        if first & marker:
            if pos + n > len(data):
                return None, 0
            return int.from_bytes(data[pos:pos + n], 'big') & mask, n
    return None, 0


# RFC 8794 Section 6 - https://www.rfc-editor.org/rfc/rfc8794#name-element-data-size
def encode_length(length):
    for marker, mask, n in _VINT_MASKS:
        if length < mask:
            marker_shifted = marker << ((n - 1) * 8)
            return (length | marker_shifted).to_bytes(n, 'big')
    raise ValueError(f'EBML length {length} too large')


# RFC 8794 Section 5 - https://www.rfc-editor.org/rfc/rfc8794#name-element-id
def encode_element_id(element_id):
    if element_id <= 0xFF:
        return bytes([element_id])
    elif element_id <= 0xFFFF:
        return element_id.to_bytes(2, 'big')
    elif element_id <= 0xFFFFFF:
        return element_id.to_bytes(3, 'big')
    else:
        return element_id.to_bytes(4, 'big')


# RFC 8794 Section 7.2 - https://www.rfc-editor.org/rfc/rfc8794#name-unsigned-integer-element
def encode_uint(element_id, value):
    if value == 0:
        payload = b'\x00'
    else:
        byte_len = (value.bit_length() + 7) // 8
        payload = value.to_bytes(byte_len, 'big')
    return encode_element_id(element_id) + encode_length(len(payload)) + payload


# RFC 8794 Section 7.5 - https://www.rfc-editor.org/rfc/rfc8794#name-utf-8-element
def encode_string(element_id, value):
    payload = value.encode('utf-8')
    return encode_element_id(element_id) + encode_length(len(payload)) + payload


# RFC 8794 Section 7.7 - https://www.rfc-editor.org/rfc/rfc8794#name-master-element
def encode_master(element_id, children_bytes):
    return encode_element_id(element_id) + encode_length(len(children_bytes)) + children_bytes


# RFC 8794 Section 5 - https://www.rfc-editor.org/rfc/rfc8794#name-element-id
def read_element_id(data, pos):
    if pos >= len(data):
        return None, 0
    first = data[pos]
    if first & 0x80:
        return first, 1
    elif first & 0x40:
        n = 2
    elif first & 0x20:
        n = 3
    elif first & 0x10:
        n = 4
    else:
        return None, 0
    if pos + n > len(data):
        return None, 0
    return int.from_bytes(data[pos:pos + n], 'big'), n


# RFC 9559 Section 20 - https://www.rfc-editor.org/rfc/rfc9559#chapters
def find_chapters(data):
    # scan top-level elements for Segment
    pos = 0
    while pos < len(data) - 4:
        eid, id_len = read_element_id(data, pos)
        if eid is None:
            break
        size, size_len = read_vint(data, pos + id_len)
        if size is None:
            break
        if eid == SEGMENT_ID:
            # scan Segment children for Chapters
            inner_pos = pos + id_len + size_len
            while inner_pos < len(data) - 4:
                inner_eid, inner_id_len = read_element_id(data, inner_pos)
                if inner_eid is None:
                    break
                inner_size, inner_size_len = read_vint(data, inner_pos + inner_id_len)
                if inner_size is None:
                    break
                total = inner_id_len + inner_size_len + inner_size
                if inner_eid == CHAPTERS_ID:
                    return inner_pos, total
                inner_pos += total
            return None
        pos += id_len + size_len + size
    return None



# RFC 9559 Section 5.1.7.1 - https://www.rfc-editor.org/rfc/rfc9559#name-editionentry-element
def encode_chapter_atom(uid, start_ns, end_ns, title, hidden=False):
    data = encode_uint(CHAPTER_UID_ID, uid)
    data += encode_uint(CHAPTER_TIME_START_ID, start_ns)
    data += encode_uint(CHAPTER_TIME_END_ID, end_ns)
    if hidden:
        data += encode_uint(CHAPTER_FLAG_HIDDEN_ID, 1)
    display = encode_string(CHAP_STRING_ID, title)
    display += encode_string(CHAP_LANGUAGE_ID, 'und')
    data += encode_master(CHAPTER_DISPLAY_ID, display)
    return encode_master(CHAPTER_ATOM_ID, data)


# RFC 9559 Section 20.1 - https://www.rfc-editor.org/rfc/rfc9559#name-editionentry
def encode_edition(uid, default, chapters_bytes, name=None):
    data = encode_uint(EDITION_UID_ID, uid)
    data += encode_uint(EDITION_FLAG_DEFAULT_ID, 1 if default else 0)
    data += encode_uint(EDITION_FLAG_ORDERED_ID, 1)
    if name:
        display = encode_string(EDITION_STRING_ID, name)
        display += encode_string(EDITION_LANGUAGE_IETF_ID, 'en')
        data += encode_master(EDITION_DISPLAY_ID, display)
    data += chapters_bytes
    return encode_master(EDITION_ENTRY_ID, data)


def replace_chapters(filepath, new_chapters_element):
    import os
    from ..utils import PostProcessingError, prepend_extension

    with open(filepath, 'rb') as f:
        data = f.read()

    result = find_chapters(data)
    if result is None:
        raise PostProcessingError('Could not find Chapters element in MK[AV] file')

    old_offset, old_size = result
    new_data = data[:old_offset] + new_chapters_element + data[old_offset + old_size:]

    temp_path = prepend_extension(filepath, 'temp')
    with open(temp_path, 'wb') as f:
        f.write(new_data)
    os.replace(temp_path, filepath)
