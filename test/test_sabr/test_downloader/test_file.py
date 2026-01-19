import tempfile
from pathlib import Path
import pytest
import uuid
from yt_dlp.downloader.sabr._io import MemoryFormatIOBackend, DiskFormatIOBackend
from yt_dlp.downloader import SabrFD
from yt_dlp import YoutubeDL
from yt_dlp.downloader.sabr._file import SequenceFile, Sequence, Segment

INIT_SEQUENCE_CONTENT_LENGTH = 1024
INIT_SEGMENT_DATA = b'\x00' * INIT_SEQUENCE_CONTENT_LENGTH


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

    def test_segment_memory_file_limit_default(self, fd, filename, init_sequence, init_segment):
        # By default, if under 2MB, should write to memory
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=init_sequence)
        init_segment.content_length = 2 * 1024 * 1024  # 2MB
        sequence_file.initialize_segment(init_segment)
        assert isinstance(sequence_file.current_segment.file, MemoryFormatIOBackend)
        sequence_file.remove()

        # If just over 2MB, should write to disk
        sequence_file = SequenceFile(fd, format_filename=filename, sequence=init_sequence)
        init_segment.content_length = 2 * 1024 * 1024 + 1  # 2MB + 1 byte
        sequence_file.initialize_segment(init_segment)
        assert isinstance(sequence_file.current_segment.file, DiskFormatIOBackend)
        sequence_file.remove()

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

        # Write some data
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
