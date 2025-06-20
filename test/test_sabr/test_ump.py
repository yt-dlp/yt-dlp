import io
import pytest

from yt_dlp.extractor.youtube._streaming.ump import varint_size, read_varint, UMPDecoder, UMPPartId


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
    # 1 byte long varint
    (b'\x01', 1),
    (b'\x4F', 79),
    # 2 byte long varint
    (b'\x80\x01', 64),
    (b'\x8A\x7F', 8138),
    (b'\xBF\x7F', 8191),
    # 3 byte long varint
    (b'\xC0\x80\x01', 12288),
    (b'\xDF\x7F\xFF', 2093055),
    # 4 byte long varint
    (b'\xE0\x80\x80\x01', 1574912),
    (b'\xEF\x7F\xFF\xFF', 268433407),
    # 5 byte long varint
    (b'\xF0\x80\x80\x80\x01', 25198720),
    (b'\xFF\x7F\xFF\xFF\xFF', 4294967167),
],
)
def test_readvarint(data, expected):
    assert read_varint(io.BytesIO(data)) == expected


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
        # Create a mock file-like object
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)

        # Create an instance of UMPDecoder with the mock file
        decoder = UMPDecoder(mock_file)

        # Iterate over the parts and check the values
        for idx, part in enumerate(decoder.iter_parts()):
            assert part.part_id == self.EXAMPLE_PART_DATA[idx]['part_id']
            assert part.size == self.EXAMPLE_PART_DATA[idx]['part_size']
            assert part.data.read() == self.EXAMPLE_PART_DATA[idx]['part_data_bytes']

        assert mock_file.closed

    def test_unexpected_eof(self):
        # Unexpected bytes at the end of the file
        mock_file = io.BytesIO(self.COMBINED_PART_DATA + b'\x00')
        decoder = UMPDecoder(mock_file)

        # Iterate over the parts and check the values
        with pytest.raises(EOFError, match='Unexpected EOF while reading part size'):
            for idx, part in enumerate(decoder.iter_parts()):
                assert part.part_id == self.EXAMPLE_PART_DATA[idx]['part_id']
                part.data.read()

        assert mock_file.closed
