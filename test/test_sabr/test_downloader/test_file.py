import dataclasses
import tempfile
from pathlib import Path
import pytest
import uuid
from yt_dlp.utils._utils import DownloadError
from yt_dlp.downloader.sabr._io import MemoryFormatIOBackend, DiskFormatIOBackend
from yt_dlp.downloader import SabrFD
from yt_dlp import YoutubeDL
from yt_dlp.downloader.sabr._file import SequenceFile, Sequence, Segment, SegmentFile

INIT_SEQUENCE_CONTENT_LENGTH = 1024
INIT_SEGMENT_DATA = b'\x00' * INIT_SEQUENCE_CONTENT_LENGTH

GENERAL_SEGMENT_CONTENT_LENGTH = 2048
GENERAL_SEGMENT_DATA = b'\x00' * GENERAL_SEGMENT_CONTENT_LENGTH


@pytest.fixture
def filename():
    # use tmp file module to generate a temporary filename
    with tempfile.TemporaryDirectory() as tmp:
        yield str(Path(tmp) / f'{uuid.uuid4()}.mp4')


@pytest.fixture
def init_segment():
    return Segment(
        segment_id='i',
        content_length=INIT_SEQUENCE_CONTENT_LENGTH,
        is_init_segment=True,
    )


def generate_segment(segment_number: int, content_length: int = GENERAL_SEGMENT_CONTENT_LENGTH) -> Segment:
    return Segment(
        segment_id=str(segment_number),
        sequence_number=segment_number,
        content_length=content_length,
        is_init_segment=False,
    )


@pytest.fixture
def general_sequence():
    return Sequence(
        sequence_id='1',
    )


@pytest.fixture
def init_sequence():
    return Sequence(
        sequence_id='i',
    )


@pytest.fixture
def fd():
    with YoutubeDL() as ydl:
        yield SabrFD(ydl, {})


@pytest.fixture
def backend(fd, filename):
    return MemoryFormatIOBackend(
        fd=fd,
        filename=filename,
    )


class TestSequenceFile:
    def test_init_sequence(self, fd, filename, init_sequence, init_segment, backend):
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=init_sequence)
        sequence_file_filename = sequence_file.file.filename
        assert sequence_file_filename == '' + str(filename) + '.sqi.sabr.part'
        assert sequence_file.is_current_segment('i') is False
        assert sequence_file.is_next_segment(init_segment) is True
        assert sequence_file.current_segment is None
        assert Path(sequence_file_filename).exists() is False
        assert sequence_file.sequence_id == 'i'

        # 1. Initialize the segment
        sequence_file.initialize_segment(init_segment)
        assert sequence_file.current_segment is not None
        segment_filename = str(filename) + '.sgi.sabr.part'
        assert sequence_file.current_segment.file.filename == segment_filename
        assert Path(sequence_file_filename).exists() is False

        # 2. Write data to the segment
        sequence_file.write_segment_data(INIT_SEGMENT_DATA, init_segment.segment_id)
        assert sequence_file.current_segment.current_length == INIT_SEQUENCE_CONTENT_LENGTH
        # No data should be in the sequence file yet
        assert sequence_file.sequence.sequence_content_length == 0
        assert Path(sequence_file_filename).exists() is False

        # 3. Finalize the segment. The segment should get merged into the sequence file
        sequence_file.end_segment(init_segment.segment_id)
        assert sequence_file.current_segment is None
        assert sequence_file.sequence.sequence_content_length == INIT_SEQUENCE_CONTENT_LENGTH
        assert sequence_file.sequence.first_segment == init_segment
        assert sequence_file.sequence.last_segment == init_segment
        assert Path(sequence_file_filename).exists() is True

        # 4. Read data from the sequence file into a backend
        sequence_file.close()
        backend.initialize_writer()
        sequence_file.read_into(backend)
        backend.close()
        backend.initialize_reader()
        data = backend.reader.read()
        assert data == INIT_SEGMENT_DATA
        backend.close()

    def test_multiple_segments(self, fd, filename, general_sequence, backend):
        # Should write multiple segments to the sequence file correctly
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)
        # Segment one
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        assert sequence_file.sequence.sequence_content_length == GENERAL_SEGMENT_CONTENT_LENGTH
        assert sequence_file.sequence.first_segment == segment_one
        assert sequence_file.sequence.last_segment == segment_one
        # Segment two
        sequence_file.initialize_segment(segment_two)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_two.segment_id)
        sequence_file.end_segment(segment_two.segment_id)
        assert sequence_file.sequence.sequence_content_length == 2 * GENERAL_SEGMENT_CONTENT_LENGTH
        assert sequence_file.sequence.first_segment == segment_one
        assert sequence_file.sequence.last_segment == segment_two
        # Read data
        sequence_file.close()
        backend.initialize_writer()
        sequence_file.read_into(backend)
        backend.close()
        backend.initialize_reader()
        data = backend.reader.read()
        assert data == GENERAL_SEGMENT_DATA + GENERAL_SEGMENT_DATA
        backend.close()

    @pytest.mark.parametrize(
        'segment_backend,segment_memory_file_limit',
        [
            (MemoryFormatIOBackend, None),  # default (2MB)
            (DiskFormatIOBackend, INIT_SEQUENCE_CONTENT_LENGTH - 1),  # disk backend: force disk by setting limit smaller than segment
        ],
        ids=['memory', 'disk'],
    )
    def test_reinitialize_segment(self, fd, filename, init_sequence, init_segment, backend, segment_backend, segment_memory_file_limit):
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=init_sequence, segment_memory_file_limit=segment_memory_file_limit)

        # Initialize the segment
        sequence_file.initialize_segment(init_segment)
        assert sequence_file.current_segment is not None
        assert isinstance(sequence_file.current_segment.file, segment_backend)

        # Write some data and do not finalize yet
        sequence_file.write_segment_data(INIT_SEGMENT_DATA, init_segment.segment_id)
        assert sequence_file.current_segment.current_length == INIT_SEQUENCE_CONTENT_LENGTH
        original_segment_file = sequence_file.current_segment.file

        # Re-initialize the same segment (e.g, due to a retry)
        sequence_file.initialize_segment(init_segment)
        assert sequence_file.current_segment is not None
        assert sequence_file.current_segment.current_length == 0
        assert isinstance(sequence_file.current_segment.file, segment_backend)
        assert sequence_file.current_segment.file is not original_segment_file

        # Write data again
        sequence_file.write_segment_data(INIT_SEGMENT_DATA, init_segment.segment_id)
        assert sequence_file.current_segment.current_length == INIT_SEQUENCE_CONTENT_LENGTH

        sequence_file.end_segment(init_segment.segment_id)

        # Check the data is correct
        sequence_file.close()
        backend.initialize_writer()
        sequence_file.read_into(backend)
        backend.close()
        backend.initialize_reader()
        data = backend.reader.read()
        assert data == INIT_SEGMENT_DATA
        backend.close()

    def test_segment_memory_file_limit_custom(self, fd, filename, init_sequence, init_segment):
        # Should be able to configure memory file limit from sequence
        sequence_file = SequenceFile(
            fd, format_filename=filename, sequence=init_sequence,
            segment_memory_file_limit=INIT_SEQUENCE_CONTENT_LENGTH - 1,
        )
        assert INIT_SEQUENCE_CONTENT_LENGTH < 2 * 1024 * 1024  # sanity check
        init_segment.content_length = INIT_SEQUENCE_CONTENT_LENGTH
        sequence_file.initialize_segment(init_segment)
        assert isinstance(sequence_file.current_segment.file, DiskFormatIOBackend)
        sequence_file.remove()

    def test_remove_existing_sequence_file_no_resume(self, fd, filename, general_sequence):
        sequence_file = SequenceFile(
            fd, format_filename=filename,
            sequence=dataclasses.replace(general_sequence), segment_memory_file_limit=1)
        assert isinstance(sequence_file.file, DiskFormatIOBackend)
        segment_one = generate_segment(1)
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        sequence_file.close()
        assert sequence_file.file.exists() is True
        assert Path(sequence_file.file.filename).exists() is True
        sequence_file.close()

        # New sequence file for the same sequence should remove existing file
        new_sequence_file = SequenceFile(
            fd, format_filename=filename, sequence=dataclasses.replace(general_sequence),
            segment_memory_file_limit=1, resume=False)
        assert new_sequence_file.file.exists() is False
        assert Path(new_sequence_file.file.filename).exists() is False
        assert Path(sequence_file.file.filename).exists() is False
        new_sequence_file.close()

    def test_remove_existing_sequence_file_missing_last_segment(self, fd, filename, general_sequence):
        # Should remove existing sequence file if last_segment info is missing
        # This should not raise an error even though resume is True (todo: confirm desired behavior)
        sequence_file = SequenceFile(
            fd, format_filename=filename,
            sequence=dataclasses.replace(general_sequence), segment_memory_file_limit=1)
        assert isinstance(sequence_file.file, DiskFormatIOBackend)
        segment_one = generate_segment(1)
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        sequence_file.close()
        assert sequence_file.file.exists() is True
        assert Path(sequence_file.file.filename).exists() is True
        sequence_file.close()

        # New sequence file for the same sequence should remove existing file
        assert general_sequence.last_segment is None
        new_sequence_file = SequenceFile(
            fd, format_filename=filename, sequence=dataclasses.replace(general_sequence),
            segment_memory_file_limit=1, resume=True)
        assert new_sequence_file.file.exists() is False
        assert Path(new_sequence_file.file.filename).exists() is False
        assert Path(sequence_file.file.filename).exists() is False
        new_sequence_file.close()

    def test_error_last_segment_provided_not_resuming(self, fd, filename, general_sequence):
        # Should raise an error if last_segment is provided but resume is False
        # TODO: error might not be correct behavior, confirm desired behavior
        general_sequence.last_segment = generate_segment(1)
        with pytest.raises(DownloadError) as excinfo:
            SequenceFile(
                fd, format_filename=filename, sequence=general_sequence,
                segment_memory_file_limit=1, resume=False)
        assert 'Cannot find existing sequence 1 file' in str(excinfo.value)

    def test_resume_no_sequence_file_found(self, fd, filename, general_sequence):
        # Should raise an error if resume is True but no existing sequence file is found
        general_sequence.last_segment = generate_segment(1)
        with pytest.raises(DownloadError) as excinfo:
            SequenceFile(
                fd, format_filename=filename, sequence=general_sequence,
                segment_memory_file_limit=1, resume=True)
        assert 'Cannot find existing sequence 1 file' in str(excinfo.value)

    def test_resume_no_content_length_provided(self, fd, filename, general_sequence):
        # Should raise an error if resume is True but no content length is provided (defaults to 0)
        sequence_file = SequenceFile(
            fd, format_filename=filename,
            sequence=dataclasses.replace(general_sequence), segment_memory_file_limit=1)
        assert isinstance(sequence_file.file, DiskFormatIOBackend)
        segment_one = generate_segment(1)
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        sequence_file.close()
        assert sequence_file.file.exists() is True
        assert Path(sequence_file.file.filename).exists() is True
        sequence_file.close()

        # New sequence file for the same sequence should raise error due to invalid content length
        general_sequence.last_segment = generate_segment(1, content_length=0)
        with pytest.raises(DownloadError) as excinfo:
            SequenceFile(
                fd, format_filename=filename, sequence=general_sequence,
                segment_memory_file_limit=1, resume=True)
        assert 'Existing sequence 1 file is not valid; removing' in str(excinfo.value)

    def test_resume_mismatch_content_length(self, fd, filename, general_sequence):
        # Should raise an error if resume is True but content length does not match
        sequence_file = SequenceFile(
            fd, format_filename=filename,
            sequence=dataclasses.replace(general_sequence), segment_memory_file_limit=1)
        assert isinstance(sequence_file.file, DiskFormatIOBackend)
        segment_one = generate_segment(1)
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        sequence_file.close()
        assert sequence_file.file.exists() is True
        assert Path(sequence_file.file.filename).exists() is True
        sequence_file.close()

        # New sequence file for the same sequence should raise error due to invalid content length
        general_sequence.last_segment = generate_segment(1, content_length=123)
        with pytest.raises(DownloadError) as excinfo:
            SequenceFile(
                fd, format_filename=filename, sequence=general_sequence,
                segment_memory_file_limit=1, resume=True)
        assert 'Existing sequence 1 file is not valid; removing' in str(excinfo.value)

    def test_resume_successful(self, fd, filename, general_sequence, backend):
        # Should successfully resume if content length matches
        sequence_file = SequenceFile(
            fd, format_filename=filename,
            sequence=dataclasses.replace(general_sequence), segment_memory_file_limit=1)
        assert isinstance(sequence_file.file, DiskFormatIOBackend)
        segment_one = generate_segment(1)
        assert sequence_file.is_next_segment(segment_one)
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        assert sequence_file.current_length == GENERAL_SEGMENT_CONTENT_LENGTH
        assert sequence_file.sequence.first_segment == segment_one
        assert sequence_file.sequence.last_segment == segment_one
        assert sequence_file.file.exists() is True
        assert Path(sequence_file.file.filename).exists() is True
        sequence_file.close()

        resume_sequence = dataclasses.replace(sequence_file.sequence)

        # New sequence file for the same sequence should succeed in resuming
        resumed_sequence_file = SequenceFile(
            fd, format_filename=filename, sequence=resume_sequence,
            segment_memory_file_limit=1, resume=True)
        assert resumed_sequence_file.file.exists() is True
        assert Path(resumed_sequence_file.file.filename).exists() is True
        assert resumed_sequence_file.current_length == GENERAL_SEGMENT_CONTENT_LENGTH
        assert resumed_sequence_file.sequence.first_segment == segment_one
        assert resumed_sequence_file.sequence.last_segment == segment_one

        # Resume: write segment two
        segment_two = generate_segment(2)
        assert not resumed_sequence_file.is_next_segment(segment_one)
        assert resumed_sequence_file.is_next_segment(segment_two)
        resumed_sequence_file.initialize_segment(segment_two)
        resumed_sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_two.segment_id)
        resumed_sequence_file.end_segment(segment_two.segment_id)
        assert resumed_sequence_file.current_length == 2 * GENERAL_SEGMENT_CONTENT_LENGTH
        assert resumed_sequence_file.sequence.first_segment == segment_one
        assert resumed_sequence_file.sequence.last_segment == segment_two
        # Read data
        resumed_sequence_file.close()
        backend.initialize_writer()
        resumed_sequence_file.read_into(backend)
        backend.close()
        backend.initialize_reader()
        data = backend.reader.read()
        assert data == GENERAL_SEGMENT_DATA + GENERAL_SEGMENT_DATA
        backend.close()

    def test_multiple_segment_parts(self, fd, filename, general_sequence, backend):
        # Should handle multiple data parts for a single segment correctly
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)

        sequence_file.initialize_segment(segment_one)
        part_one = b'\x00' * (GENERAL_SEGMENT_CONTENT_LENGTH // 2)
        part_two = b'\x00' * (GENERAL_SEGMENT_CONTENT_LENGTH // 2)
        assert sequence_file.is_current_segment(segment_one.segment_id)
        assert sequence_file.current_length == 0

        # Write data in two parts
        sequence_file.write_segment_data(part_one, segment_one.segment_id)
        assert sequence_file.current_length == GENERAL_SEGMENT_CONTENT_LENGTH // 2
        sequence_file.write_segment_data(part_two, segment_one.segment_id)
        assert sequence_file.current_length == GENERAL_SEGMENT_CONTENT_LENGTH
        sequence_file.end_segment(segment_one.segment_id)

        assert not sequence_file.is_current_segment(segment_one.segment_id)
        assert sequence_file.sequence.sequence_content_length == GENERAL_SEGMENT_CONTENT_LENGTH
        assert sequence_file.sequence.first_segment == segment_one
        assert sequence_file.sequence.last_segment == segment_one

        sequence_file.close()
        backend.initialize_writer()
        sequence_file.read_into(backend)
        backend.close()
        backend.initialize_reader()
        data = backend.reader.read()
        assert data == part_one + part_two
        backend.close()

    def test_empty_segment(self, fd, filename, general_sequence, backend):
        # Segment with a content length of 0 should be handled correctly
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1, content_length=0)
        sequence_file.initialize_segment(segment_one)
        assert sequence_file.is_current_segment(segment_one.segment_id)
        assert sequence_file.current_length == 0
        sequence_file.end_segment(segment_one.segment_id)
        assert not sequence_file.is_current_segment(segment_one.segment_id)
        assert sequence_file.sequence.sequence_content_length == 0
        assert sequence_file.sequence.first_segment == segment_one
        assert sequence_file.sequence.last_segment == segment_one
        sequence_file.remove()

    def test_next_segment_current_segment_exists(self, fd, filename, general_sequence):
        # is_next_segment should return False if there is a current segment
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)

        sequence_file.initialize_segment(segment_one)
        assert sequence_file.is_current_segment(segment_one.segment_id) is True
        assert sequence_file.is_next_segment(segment_two) is False

        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)

        assert sequence_file.is_current_segment(segment_one.segment_id) is False
        assert sequence_file.is_next_segment(segment_two) is True

        sequence_file.remove()

    def test_next_segment_reject_after_init_segment(self, fd, filename, general_sequence):
        # is_next_segment should return False if the previous segment was an init segment
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        init_segment = Segment(
            segment_id='i',
            content_length=INIT_SEQUENCE_CONTENT_LENGTH,
            is_init_segment=True,
        )

        assert sequence_file.is_next_segment(init_segment) is True
        sequence_file.initialize_segment(init_segment)
        sequence_file.write_segment_data(INIT_SEGMENT_DATA, init_segment.segment_id)
        sequence_file.end_segment(init_segment.segment_id)
        # Do not allow another init segment after an init segment
        assert sequence_file.is_next_segment(Segment(
            segment_id='i',
            content_length=INIT_SEQUENCE_CONTENT_LENGTH,
            is_init_segment=True,
        )) is False

        # Do not allow a regular segment immediately after an init segment
        assert sequence_file.is_next_segment(generate_segment(1)) is False

        sequence_file.remove()

    def test_next_segment_non_consecutive(self, fd, filename, general_sequence):
        # is_next_segment should return False if the segment number is not consecutive
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)
        segment_three = generate_segment(3)

        assert sequence_file.is_next_segment(segment_one) is True
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        assert sequence_file.sequence.first_segment == segment_one
        assert sequence_file.sequence.last_segment == segment_one

        # Segment three is not the next consecutive segment
        assert sequence_file.is_next_segment(segment_three) is False

        # Segment two is the next consecutive segment
        assert sequence_file.is_next_segment(segment_two) is True

        sequence_file.remove()

    def test_max_segments(self, fd, filename, general_sequence):
        # is_next_segment should respect max_segments limit
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence, max_segments=2)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)
        segment_three = generate_segment(3)

        assert sequence_file.is_next_segment(segment_one) is True
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)

        assert sequence_file.is_next_segment(segment_two) is True
        sequence_file.initialize_segment(segment_two)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_two.segment_id)
        sequence_file.end_segment(segment_two.segment_id)

        # Now max_segments reached; segment three should not be allowed
        assert sequence_file.is_next_segment(segment_three) is False

        sequence_file.remove()

    def test_max_segments_zero_index(self, fd, filename, general_sequence):
        # is_next_segment should respect max_segments limit when starting from segment number 0
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence, max_segments=2)
        segment_zero = generate_segment(0)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)
        assert sequence_file.is_next_segment(segment_zero) is True
        sequence_file.initialize_segment(segment_zero)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_zero.segment_id)
        sequence_file.end_segment(segment_zero.segment_id)

        assert sequence_file.is_next_segment(segment_one) is True
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)
        # Now max_segments reached; segment two should not be allowed
        assert sequence_file.is_next_segment(segment_two) is False

        sequence_file.remove()

    def test_reinitialize_different_segment_error(self, fd, filename, general_sequence):
        # Should raise an error when trying to reinitialize a different segment
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)

        sequence_file.initialize_segment(segment_one)
        with pytest.raises(ValueError) as excinfo:
            sequence_file.initialize_segment(segment_two)
        assert 'Cannot reinitialize a segment that does not match the current segment' in str(excinfo.value)

        sequence_file.remove()

    def test_initialize_non_next_segment_error(self, fd, filename, general_sequence):
        # Should raise an error when trying to initialize a non-next segment
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)

        # Init segment is allowed as the first segment
        segment_one = generate_segment(1)
        sequence_file.initialize_segment(segment_one)
        sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_one.segment_id)
        sequence_file.end_segment(segment_one.segment_id)

        # Now try to initialize segment three instead of segment two
        segment_three = generate_segment(3)
        with pytest.raises(ValueError) as excinfo:
            sequence_file.initialize_segment(segment_three)
        assert 'Cannot initialize a segment that does not match the next segment' in str(excinfo.value)
        sequence_file.remove()

    def test_write_non_current_segment_error(self, fd, filename, general_sequence):
        # Should raise an error when trying to write to a non-current segment
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)

        sequence_file.initialize_segment(segment_one)
        with pytest.raises(ValueError) as excinfo:
            sequence_file.write_segment_data(GENERAL_SEGMENT_DATA, segment_two.segment_id)
        assert 'Cannot write to a segment that does not match the current segment' in str(excinfo.value)

        sequence_file.remove()

    def test_end_non_current_segment_error(self, fd, filename, general_sequence):
        # Should raise an error when trying to end a non-current segment
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_two = generate_segment(2)

        sequence_file.initialize_segment(segment_one)
        with pytest.raises(ValueError) as excinfo:
            sequence_file.end_segment(segment_two.segment_id)
        assert 'Cannot end a segment that does not exist' in str(excinfo.value)

        sequence_file.remove()

    def test_close_without_segments(self, fd, filename, general_sequence):
        # Should be able to close a sequence file without any segments initialized
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        sequence_file.close()
        assert sequence_file.file.exists() is False

    def test_remove_without_segments(self, fd, filename, general_sequence):
        # Should be able to remove a sequence file without any segments initialized
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        sequence_file.remove()
        assert sequence_file.file.exists() is False

    def test_end_segment_content_length_mismatch(self, fd, filename, general_sequence):
        # Should raise an error if the written content length does not match the segment's content length
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)

        sequence_file.initialize_segment(segment_one)
        # Write less data than the segment's content length
        sequence_file.write_segment_data(b'\x00' * (GENERAL_SEGMENT_CONTENT_LENGTH - 1), segment_one.segment_id)

        with pytest.raises(DownloadError) as excinfo:
            sequence_file.end_segment(segment_one.segment_id)
        assert 'Filesize mismatch for segment 1: Expected 2048 bytes, got 2047 bytes' in str(excinfo.value)

        sequence_file.remove()

    def test_end_segment_content_length_none(self, fd, filename, general_sequence):
        # Should not raise an error if the segment's content length was not provided (defaults to 0)
        # TODO: should this fail? Confirm desired behavior
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_one.content_length = 0  # content length not provided

        sequence_file.initialize_segment(segment_one)
        # Write some data
        sequence_file.write_segment_data(b'\x00' * (GENERAL_SEGMENT_CONTENT_LENGTH - 1), segment_one.segment_id)

        # Should not raise an error
        sequence_file.end_segment(segment_one.segment_id)

        sequence_file.remove()

    def test_end_segment_content_length_estimated(self, fd, filename, general_sequence):
        # Should not raise an error if the segment's content length is estimated
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=general_sequence)
        segment_one = generate_segment(1)
        segment_one.content_length_estimated = True

        sequence_file.initialize_segment(segment_one)
        # Write less data than the segment's content length
        sequence_file.write_segment_data(b'\x00' * (GENERAL_SEGMENT_CONTENT_LENGTH - 1), segment_one.segment_id)

        # Should not raise an error
        sequence_file.end_segment(segment_one.segment_id)

        # Sequence file should reflect the actual written length
        assert sequence_file.sequence.sequence_content_length == GENERAL_SEGMENT_CONTENT_LENGTH - 1
        sequence_file.remove()


class TestSegmentFile:
    def test_init_segment_file_memory(self, fd, filename, init_segment, backend):
        segment_file = SegmentFile(fd, format_filename=filename, segment=init_segment)
        assert segment_file.file.exists() is False
        assert isinstance(segment_file.file, MemoryFormatIOBackend)
        assert segment_file.segment_id == 'i'

        assert not segment_file.file.mode

        # Write data
        segment_file.write(INIT_SEGMENT_DATA[:INIT_SEQUENCE_CONTENT_LENGTH // 2])
        assert segment_file.current_length == INIT_SEQUENCE_CONTENT_LENGTH // 2
        assert segment_file.file.mode

        segment_file.write(INIT_SEGMENT_DATA[INIT_SEQUENCE_CONTENT_LENGTH // 2:])
        assert segment_file.current_length == INIT_SEQUENCE_CONTENT_LENGTH

        segment_file.finish_write()
        assert segment_file.file.exists() is True

        backend.initialize_writer()
        segment_file.read_into(backend)
        backend.close()
        backend.initialize_reader()
        data = backend.reader.read()
        assert data == INIT_SEGMENT_DATA
        backend.close()

        segment_file.remove()
        assert segment_file.file.exists() is False

    def test_init_segment_file_disk(self, fd, filename, init_segment, backend):
        data_part_one = b'\x00' * (1024 * 1024)  # 1MB
        data_part_two = b'\x00' * (1024 * 1024 + 1)  # 1MB + 1 bytes
        content_length = len(data_part_one) + len(data_part_two)
        assert len(data_part_one) + len(data_part_two) == content_length

        init_segment.content_length = content_length
        segment_file = SegmentFile(fd, format_filename=filename, segment=init_segment)
        assert segment_file.file.exists() is False
        assert segment_file.file.filename == filename + f'.sg{init_segment.segment_id}.sabr.part'
        assert isinstance(segment_file.file, DiskFormatIOBackend)
        assert segment_file.segment_id == 'i'

        assert not segment_file.file.mode

        # Write data
        segment_file.write(data_part_one)
        assert segment_file.current_length == content_length // 2
        assert segment_file.file.mode

        segment_file.write(data_part_two)
        assert segment_file.current_length == content_length

        segment_file.finish_write()
        assert segment_file.file.exists() is True

        assert Path(filename + f'.sg{init_segment.segment_id}.sabr.part').exists() is True

        backend.initialize_writer()
        segment_file.read_into(backend)
        backend.close()
        backend.initialize_reader()
        data = backend.reader.read()
        assert data == data_part_one + data_part_two
        backend.close()

        segment_file.remove()
        assert segment_file.file.exists() is False
        assert Path(filename + f'.sg{init_segment.segment_id}.sabr.part').exists() is False

    def test_segment_memory_file_limit_default(self, fd, filename, init_segment):
        # By default, if under 2MB, should write to memory
        init_segment.content_length = 2 * 1024 * 1024  # 2MB
        segment_file = SegmentFile(fd, format_filename=filename, segment=init_segment)
        assert isinstance(segment_file.file, MemoryFormatIOBackend)
        segment_file.remove()

        # If just over 2MB, should write to disk
        init_segment.content_length = 2 * 1024 * 1024 + 1  # 2MB + 1 byte
        segment_file = SegmentFile(fd, format_filename=filename, segment=init_segment)
        assert isinstance(segment_file.file, DiskFormatIOBackend)
        segment_file.remove()

    def test_segment_memory_file_limit_custom(self, fd, filename, init_segment):
        # Should be able to configure memory file limit from segment
        assert INIT_SEQUENCE_CONTENT_LENGTH < 2 * 1024 * 1024  # sanity check
        init_segment.content_length = INIT_SEQUENCE_CONTENT_LENGTH
        segment_file = SegmentFile(
            fd, format_filename=filename,
            segment=init_segment, memory_file_limit=INIT_SEQUENCE_CONTENT_LENGTH - 1)
        assert isinstance(segment_file.file, DiskFormatIOBackend)
        segment_file.remove()

    def test_remove_existing_segment_file(self, fd, filename, init_segment):
        segment_file = SegmentFile(fd, format_filename=filename, segment=init_segment, memory_file_limit=1)
        assert isinstance(segment_file.file, DiskFormatIOBackend)
        segment_file.write(INIT_SEGMENT_DATA)
        segment_file.finish_write()
        assert segment_file.file.exists() is True
        assert Path(segment_file.file.filename).exists() is True
        segment_file.close()

        # New segment file for the same segment should remove existing file
        new_segment_file = SegmentFile(fd, format_filename=filename, segment=init_segment, memory_file_limit=1)
        assert new_segment_file.file.exists() is False
        assert Path(new_segment_file.file.filename).exists() is False
        assert Path(segment_file.file.filename).exists() is False
