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
    UMPPartStream,
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


def test_ump_part_id_unknown():
    # Should create an unknown part ID for undefined values
    unknown_id = UMPPartId(9999)
    assert unknown_id.value == 9999
    assert unknown_id.name == 'UNKNOWN_9999'


class _UnexpectedEOFBytesIO(io.BytesIO):
    def __init__(self, data, max_read):
        super().__init__(data)
        self.max_read = max_read

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.max_read
        else:
            size = min(size, self.max_read)
        return super().read(size)


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
            'part_id': UMPPartId(4294967295),
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

    COMBINED_PART_DATA = b''.join(
        part['part_type_bytes'] + part['part_size_bytes'] + part['part_data_bytes'] for part in EXAMPLE_PART_DATA)

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

    def test_read_part_independent(self):
        # reading one part's data should not read beyond its declared size
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)
        parts = decoder.iter_parts()

        part1 = next(parts)
        assert part1.part_id == self.EXAMPLE_PART_DATA[0]['part_id']
        assert part1.size == self.EXAMPLE_PART_DATA[0]['part_size']
        assert part1.data.read(9999) == self.EXAMPLE_PART_DATA[0]['part_data_bytes']
        assert mock_file.tell() == len(
            self.EXAMPLE_PART_DATA[0]['part_type_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_size_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_data_bytes'])

        part2 = next(parts)
        assert part2.part_id == self.EXAMPLE_PART_DATA[1]['part_id']
        assert part2.size == self.EXAMPLE_PART_DATA[1]['part_size']
        assert part2.data.read() == self.EXAMPLE_PART_DATA[1]['part_data_bytes']

    def test_drain_if_not_read(self):
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)
        part_iter = decoder.iter_parts()

        part1 = next(part_iter)
        part1_position = mock_file.tell()

        assert part1_position == len(self.EXAMPLE_PART_DATA[0]['part_type_bytes'] + self.EXAMPLE_PART_DATA[0]['part_size_bytes'])

        # should auto-drain part1 data when requesting next part
        part2 = next(part_iter)
        part2_position = mock_file.tell()
        assert part2_position == len(
            self.EXAMPLE_PART_DATA[0]['part_type_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_size_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_data_bytes']
            + self.EXAMPLE_PART_DATA[1]['part_type_bytes']
            + self.EXAMPLE_PART_DATA[1]['part_size_bytes'],
        )
        assert part1_position != part2_position

        assert part1.part_id == self.EXAMPLE_PART_DATA[0]['part_id']
        assert part2.part_id == self.EXAMPLE_PART_DATA[1]['part_id']
        assert not part1.data.closed
        assert part1.data.read() == self.EXAMPLE_PART_DATA[0]['part_data_bytes']
        assert part2.data.read() == self.EXAMPLE_PART_DATA[1]['part_data_bytes']

    def test_explicit_drain(self):
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)
        part_iter = decoder.iter_parts()

        part1 = next(part_iter)
        part1.data.drain()
        assert mock_file.tell() == len(
            self.EXAMPLE_PART_DATA[0]['part_type_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_size_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_data_bytes'])

        assert part1.part_id == self.EXAMPLE_PART_DATA[0]['part_id']
        assert part1.data.read() == self.EXAMPLE_PART_DATA[0]['part_data_bytes']

        part2 = next(part_iter)
        assert part2.part_id == self.EXAMPLE_PART_DATA[1]['part_id']

    def test_explicit_drain_after_partial_read(self):
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)
        part_iter = decoder.iter_parts()

        part1 = next(part_iter)
        first_chunk = part1.data.read(11)
        part1.data.drain()

        assert first_chunk == self.EXAMPLE_PART_DATA[0]['part_data_bytes'][:11]
        assert part1.data.read() == self.EXAMPLE_PART_DATA[0]['part_data_bytes'][11:]

        part2 = next(part_iter)
        assert part2.part_id == self.EXAMPLE_PART_DATA[1]['part_id']

    def test_drain_after_partial_read(self):
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)
        part_iter = decoder.iter_parts()

        part1 = next(part_iter)
        tell_before_read = mock_file.tell()
        initial = part1.data.read(11)
        assert mock_file.tell() == tell_before_read + 11

        part2 = next(part_iter)

        assert initial == self.EXAMPLE_PART_DATA[0]['part_data_bytes'][:11]
        assert not part1.data.closed
        assert part1.data.read() == self.EXAMPLE_PART_DATA[0]['part_data_bytes'][11:]
        assert part2.part_id == self.EXAMPLE_PART_DATA[1]['part_id']

    def test_consumer_drain_close_then_advance(self):
        # Should not fail if the consumer drains and closes the part data
        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)
        part_iter = decoder.iter_parts()

        part1 = next(part_iter)
        part1.data.drain()
        part1.data.close()
        assert mock_file.tell() == len(
            self.EXAMPLE_PART_DATA[0]['part_type_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_size_bytes']
            + self.EXAMPLE_PART_DATA[0]['part_data_bytes'])

        part2 = next(part_iter)
        assert part2.part_id == self.EXAMPLE_PART_DATA[1]['part_id']

        assert part1.data.closed
        assert part2.data.read() == self.EXAMPLE_PART_DATA[1]['part_data_bytes']

    def test_part_closed_externally_decoder_seeks(self, monkeypatch):
        # When the consumer closes a part stream early without fully reading it or draining it,
        # the decoder must seek (read) past the remaining bytes to re-align for the next part.
        discard_called = 0
        orig_discard = UMPPartStream.discard

        def discard_spy(part_stream):
            nonlocal discard_called
            discard_called += 1
            return orig_discard(part_stream)

        monkeypatch.setattr(UMPPartStream, 'discard', discard_spy)

        mock_file = io.BytesIO(self.COMBINED_PART_DATA)
        decoder = UMPDecoder(mock_file)
        part_iter = decoder.iter_parts()

        part1 = next(part_iter)
        assert part1.data.read(7) == self.EXAMPLE_PART_DATA[0]['part_data_bytes'][:7]
        header_size = len(self.EXAMPLE_PART_DATA[0]['part_type_bytes'] + self.EXAMPLE_PART_DATA[0]['part_size_bytes'])
        assert mock_file.tell() == header_size + 7

        part1.data.close()
        assert mock_file.tell() == header_size + 7

        with pytest.raises(ValueError, match='I/O operation on closed file'):
            part1.data.read(1)

        part2 = next(part_iter)
        assert part2.part_id == self.EXAMPLE_PART_DATA[1]['part_id']
        assert discard_called == 1

    def test_decoder_seek_eof(self):
        # If the decoder needs to seek past the remaining bytes of a part due to an external close, but hits EOF,
        # it should raise an EOFError.
        # This is to ensure it is using UMPPartStream drain logic to conduct the seek
        mock_file = _UnexpectedEOFBytesIO(
            self.COMBINED_PART_DATA,
            max_read=len(
                self.EXAMPLE_PART_DATA[0]['part_type_bytes'] + self.EXAMPLE_PART_DATA[0]['part_size_bytes']) + 3)

        decoder = UMPDecoder(mock_file)
        part_iter = decoder.iter_parts()

        part1 = next(part_iter)
        part1.data.read(2)
        part1.data.close()

        assert part1.data.tell() == 2
        assert mock_file.tell() == len(
            self.EXAMPLE_PART_DATA[0]['part_type_bytes'] + self.EXAMPLE_PART_DATA[0]['part_size_bytes']) + 2

        with pytest.raises(EOFError, match=r'Unexpected EOF while reading part data \(expected 125, got 5\)'):
            next(part_iter)


class TestUMPPartStream:
    def test_attrs(self):
        data = UMPPartStream(io.BytesIO(b'abc'), 3)
        assert data.readable() is True
        assert data.writable() is False
        assert data.seekable() is False

    def test_tell_zero(self):
        data = UMPPartStream(io.BytesIO(b'abc'), 3)
        assert data.tell() == 0

    def test_remaining_initial(self):
        data = UMPPartStream(io.BytesIO(b'abcdef'), 6)
        assert data.remaining == 6

    def test_tell_after_close(self):
        data = UMPPartStream(io.BytesIO(b'abcdef'), 6)
        assert data.read(4) == b'abcd'
        assert data.tell() == 4
        data.close()
        assert data.closed
        assert data.tell() == 4

    def test_remaining_after_close(self):
        data = UMPPartStream(io.BytesIO(b'abcdef'), 6)
        assert data.read(4) == b'abcd'
        assert data.remaining == 2
        data.close()
        assert data.closed
        assert data.remaining == 2

    def test_read_all(self):
        data = UMPPartStream(io.BytesIO(b'abcdef'), 6)
        assert data.read() == b'abcdef'
        assert data.tell() == 6
        assert data.remaining == 0
        assert data.read() == b''

    def test_read_stops_at_size(self):
        fp = io.BytesIO(b'abcxyz_')
        data = UMPPartStream(fp, 3)

        assert data.read(9999) == b'abc'
        assert data.read(1) == b''
        assert data.tell() == 3
        assert fp.tell() == 3
        assert fp.read() == b'xyz_'

    def test_read_oversize(self):
        data = UMPPartStream(io.BytesIO(b'abcdef'), 6)
        assert data.read(99) == b'abcdef'
        assert data.tell() == 6

    def test_read_zero(self):
        data = UMPPartStream(io.BytesIO(b'abcdef'), 0)
        assert data.read(0) == b''
        assert data.tell() == 0
        assert data.remaining == 0

    def test_read_closed(self):
        data = UMPPartStream(io.BytesIO(b'abc'), 3)
        data.close()
        with pytest.raises(ValueError, match='I/O operation on closed file'):
            data.read(1)

    def test_drain_zero(self):
        data = UMPPartStream(io.BytesIO(b''), 0)
        data.drain()
        assert data.read() == b''
        assert data.tell() == 0
        assert data.remaining == 0

    def test_drain_closed(self):
        data = UMPPartStream(io.BytesIO(b'abc'), 3)
        data.close()
        with pytest.raises(ValueError, match='I/O operation on closed file'):
            data.drain()
        assert data.tell() == 0
        assert data.remaining == 3

    def test_drain_after_partial(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 6)
        assert data.read(2) == b'ab'
        assert fp.tell() == 2
        assert data.tell() == 2
        assert data.remaining == 4
        data.drain()
        assert data.remaining == 0
        assert data.read() == b'cdef'
        assert data.tell() == 6
        assert fp.tell() == 6

    def test_drain_then_read_chunks(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 6)
        data.drain()
        assert data.remaining == 0
        assert fp.tell() == 6
        assert data.read(2) == b'ab'
        assert data.read(2) == b'cd'
        assert data.read(2) == b'ef'
        assert data.read(2) == b''
        assert data.tell() == 6

    def test_drain_idempotent(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 6)
        data.drain()
        data.drain()
        assert data.read() == b'abcdef'
        assert data.tell() == 6
        assert fp.tell() == 6
        assert data.remaining == 0

    def test_discard(self):
        fp = io.BytesIO(b'abcdefxyz_')
        data = UMPPartStream(fp, 6)
        data.discard()
        assert data.tell() == 6
        assert data.remaining == 0
        assert data.read() == b''
        assert fp.tell() == 6
        assert fp.read() == b'xyz_'

    def test_discard_after_partial(self):
        fp = io.BytesIO(b'abcdefxyz_')
        data = UMPPartStream(fp, 6)
        assert data.read(2) == b'ab'
        data.discard()
        assert data.tell() == 6
        assert data.remaining == 0
        assert data.read() == b''
        assert fp.tell() == 6
        assert fp.read() == b'xyz_'

    def test_discard_closed(self):
        data = UMPPartStream(io.BytesIO(b'abc'), 3)
        data.close()
        with pytest.raises(ValueError, match='I/O operation on closed file'):
            data.discard()

    def test_discard_eof_error(self):
        data = UMPPartStream(_UnexpectedEOFBytesIO(b'abcdef', max_read=2), 3)
        with pytest.raises(EOFError, match=r'Unexpected EOF while reading part data \(expected 3, got 2\)'):
            data.discard()
        data.close()

    def test_readinto(self):
        fp = io.BytesIO(b'abcdefxyz_')
        data = UMPPartStream(fp, 6)

        buffer = bytearray(4)
        count = data.readinto(buffer)
        assert count == 4
        assert bytes(buffer) == b'abcd'
        assert data.tell() == 4
        assert data.remaining == 2

        remaining = data.read()
        assert remaining == b'ef'
        assert data.tell() == 6
        assert data.remaining == 0

        # should not read beyond size
        eof_buffer = bytearray(4)
        assert data.readinto(eof_buffer) == 0
        assert data.tell() == 6
        assert data.remaining == 0
        assert fp.tell() == 6
        assert fp.read() == b'xyz_'

    def test_close_does_not_drain(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 6)
        assert data.read(2) == b'ab'
        data.close()
        assert fp.tell() == 2
        assert data.remaining == 4

    def test_close_idempotent(self):
        data = UMPPartStream(io.BytesIO(b'abc'), 3)
        data.close()
        data.close()
        assert data.closed

    def test_close_clears_buffer(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 6)
        data.drain()
        assert data._buffer is not None
        data.close()
        assert data._buffer is None

    def test_close_not_close_underlying(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 3)
        data.read()
        data.close()
        assert not fp.closed
        assert fp.read() == b'def'
        assert fp.tell() == 6

    def test_underlying_file_closed_read(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 3)
        fp.close()
        with pytest.raises(ValueError, match='I/O operation on closed file'):
            data.read(1)
        data.close()

    def test_underlying_file_closed_drain(self):
        fp = io.BytesIO(b'abcdef')
        data = UMPPartStream(fp, 3)
        fp.close()
        with pytest.raises(ValueError, match='I/O operation on closed file'):
            data.drain()
        data.close()

    def test_drain_eof_error(self):
        # should raise an error if not all expected bytes are returned
        data = UMPPartStream(_UnexpectedEOFBytesIO(b'abcdef', max_read=2), 3)
        with pytest.raises(EOFError, match=r'Unexpected EOF while reading part data \(expected 3, got 2\)'):
            data.drain()
        data.close()

    def test_full_read_eof_error(self):
        # should raise an error if not all expected bytes are returned
        data = UMPPartStream(_UnexpectedEOFBytesIO(b'abcdef', max_read=2), 3)
        with pytest.raises(EOFError, match=r'Unexpected EOF while reading part data \(expected 3, got 2\)'):
            data.read()
        data.close()

    def test_partial_oversize_read_eof_error(self):
        # should raise an error if not all expected bytes are returned for an oversize partial read
        data = UMPPartStream(_UnexpectedEOFBytesIO(b'abcdef', max_read=2), 3)
        with pytest.raises(EOFError, match=r'Unexpected EOF while reading part data \(expected 3, got 2\)'):
            data.read(10)
        data.close()

    def test_partial_read_eof_error(self):
        # should raise an error if not all expected bytes are returned for a partial read
        data = UMPPartStream(_UnexpectedEOFBytesIO(b'abcdef', max_read=2), 4)
        with pytest.raises(EOFError, match=r'Unexpected EOF while reading part data \(expected 3, got 2\)'):
            data.read(3)
        data.close()


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
