import io
import pytest

from yt_dlp.extractor.youtube._streaming.ump import (
    varint_size,
    read_varint,
    UMPDecoder,
    UMPPartId,
    write_varint,
    UMPEncoder,
    UMPPart,
)


@pytest.mark.parametrize('data, expected', [
    (0x01, 1),
    (0x4F, 1),
    (0x80, 2),
    (0xBF, 2),
    (0xC0, 3),
    (0xDF, 3),
    (0xE0, 4),
    (0xEF, 4),
    (0xF0, 5),
    (0xFF, 5),
])
def test_varint_size(data, expected):
    assert varint_size(data) == expected


@pytest.mark.parametrize('data, expected', [
    (b'\x01', 1),
    (b'\xad\x05', 365),
    (b'\xd5\x22\x05', 42069),
    (b'\xe0\x68\x89\x09', 10000000),
    (b'\xf0\xff\xc9\x9a\x3b', 999999999),
    (b'\xf0\xff\xff\xff\xff', 4294967295),
],
)
def test_readvarint(data, expected):
    assert read_varint(io.BytesIO(data)) == expected


@pytest.mark.parametrize('value, expected_bytes', [
    (1, b'\x01'),
    (365, b'\xad\x05'),
    (42069, b'\xd5\x22\x05'),
    (10000000, b'\xe0\x68\x89\x09'),
    (999999999, b'\xf0\xff\xc9\x9a\x3b'),
    (4294967295, b'\xf0\xff\xff\xff\xff'),
])
def test_writevarint(value, expected_bytes):
    fp = io.BytesIO()
    write_varint(fp, value)
    assert fp.getvalue() == expected_bytes


class TestUMPDecoder:
    EXAMPLE_PART_DATA = [
        {
            # Part 1: Part type of 20, part size of 127
            'part_type_bytes': b'\x14',
            'part_size_bytes': b'\x7F',
            'part_data_bytes': b'\x01' * 127,
            'part_id': UMPPartId.MEDIA_HEADER,
            'part_size': 127,
        },
        # Part 2, Part type of 4294967295, part size of 0
        {
            'part_type_bytes': b'\xFF\xFF\xFF\xFF\xFF',
            'part_size_bytes': b'\x00',
            'part_data_bytes': b'',
            'part_id': UMPPartId.UNKNOWN,
            'part_size': 0,
        },
        # Part 3: Part type of 21, part size of 1574912
        {
            'part_type_bytes': b'\x15',
            'part_size_bytes': b'\xE0\x80\x80\x01',
            'part_data_bytes': b'\x01' * 1574912,
            'part_id': UMPPartId.MEDIA,
            'part_size': 1574912,
        },
    ]

    COMBINED_PART_DATA = b''.join(part['part_type_bytes'] + part['part_size_bytes'] + part['part_data_bytes'] for part in EXAMPLE_PART_DATA)

    def test_iter_parts(self):
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)

        for idx, part in enumerate(decoder.iter_parts()):
            assert part.part_id == self.EXAMPLE_PART_DATA[idx]['part_id']
            assert part.size == self.EXAMPLE_PART_DATA[idx]['part_size']
            assert part.data.read() == self.EXAMPLE_PART_DATA[idx]['part_data_bytes']

        assert mock_file.closed

    def test_unexpected_eof(self):
        # Unexpected bytes at the end of the file
        mock_file = io.BytesIO(self.COMBINED_PART_DATA + b'\x00')
        decoder = UMPDecoder(mock_file)

        with pytest.raises(EOFError, match='Unexpected EOF while reading part size'):
            for idx, part in enumerate(decoder.iter_parts()):
                assert part.part_id == self.EXAMPLE_PART_DATA[idx]['part_id']
                part.data.read()

        assert mock_file.closed


class TestUMPEncoder:
    def test_write_part(self):
        fp = io.BytesIO()
        encoder = UMPEncoder(fp)
        part = UMPPart(
            part_id=UMPPartId.MEDIA_HEADER,
            size=127,
            data=io.BytesIO(b'\x01' * 127),
        )

        encoder.write_part(part)

        part_type = b'\x14'  # MEDIA_HEADER part type
        part_size = b'\x7F'  # Part size of 127
        expected_data = part_type + part_size + b'\x01' * 127
        assert fp.getvalue() == expected_data
