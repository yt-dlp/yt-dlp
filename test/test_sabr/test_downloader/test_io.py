import io
import os
from unittest.mock import MagicMock
import pytest

from yt_dlp.downloader.sabr._io import (
    MemoryFormatIOBackend,
    DiskFormatIOBackend,
)


EXAMPLE_DATA = b'abc' * 10


@pytest.mark.parametrize('backend_cls', [MemoryFormatIOBackend, DiskFormatIOBackend])
class TestFormatIOBackend:
    def test_exists_and_remove(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        assert backend.exists() is False
        backend.initialize_writer()
        backend.write(EXAMPLE_DATA)
        backend.close()
        assert backend.exists() is True
        backend.remove()
        assert backend.exists() is False

    def test_initialize_double_init_error(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        with pytest.raises(ValueError, match='Backend already initialized'):
            backend.initialize_writer()
        backend.close()

        backend.initialize_reader()
        with pytest.raises(ValueError, match='Backend already initialized'):
            backend.initialize_reader()
        backend.close()

    def test_write_requires_initialized_writer(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        with pytest.raises(ValueError, match='Backend writer not initialized'):
            backend.write(EXAMPLE_DATA)

        backend.remove()

    def test_no_reader(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        assert backend.reader is None

        # If opened in write mode, reader should be None
        backend.initialize_writer()
        assert backend.reader is None
        backend.remove()

    def test_no_writer(self, fd, filename, backend_cls):
        with open(filename, 'wb') as f:
            f.write(EXAMPLE_DATA)

        backend = backend_cls(fd, filename)
        assert backend.writer is None

        # If opened in read mode, writer should be None
        backend.initialize_reader()
        assert backend.writer is None
        backend.remove()

    def test_mode(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        assert backend.mode is None

        backend.initialize_writer()
        assert backend.mode == 'write'
        backend.close()
        assert backend.mode is None

        backend.initialize_reader()
        assert backend.mode == 'read'
        backend.close()
        assert backend.mode is None

        backend.remove()

    def test_write_wrong_type(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        with pytest.raises(TypeError, match='Data must be bytes or a BufferedIOBase object'):
            backend.write('this is a string, not bytes or a file-like object')
        backend.close()
        backend.remove()

    def test_write_bytes(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        written = backend.write(EXAMPLE_DATA)
        assert written == len(EXAMPLE_DATA)
        backend.close()

        backend.initialize_reader()
        out = backend.reader.read()
        assert out == EXAMPLE_DATA
        backend.close()
        backend.remove()

    def test_write_with_buffered_io(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        bio = io.BytesIO(EXAMPLE_DATA)
        written = backend.write(bio)
        # when passing a BufferedIOBase, write returns number of bytes written
        assert written == len(EXAMPLE_DATA)
        backend.close()

        backend.initialize_reader()
        out = backend.reader.read()
        assert out == EXAMPLE_DATA
        backend.close()
        backend.remove()

    def test_read_into(self, fd, filename, backend_cls):
        src = backend_cls(fd, filename + '.src')
        dst = backend_cls(fd, filename + '.dst')

        # write data into src
        src.initialize_writer()
        src.write(EXAMPLE_DATA)
        src.close()

        # copy from src to dst using read_into
        src.initialize_reader()
        dst.initialize_writer()
        src.read_into(dst)
        dst.close()
        src.close()

        dst.initialize_reader()
        out = dst.reader.read()
        assert out == EXAMPLE_DATA
        dst.close()
        dst.remove()
        src.remove()

    def test_read_into_wrong_initialization(self, fd, filename, backend_cls):
        src = backend_cls(fd, filename + '.src')
        dst = backend_cls(fd, filename + '.dst')

        # write data into src
        src.initialize_writer()
        src.write(EXAMPLE_DATA)
        src.close()

        # Try to read_into destination without initializing destination writer
        with pytest.raises(ValueError, match='Destination backend writer not initialized'):
            src.read_into(dst)

        # Try to read_into destination without initializing source reader
        with pytest.raises(ValueError, match='Backend reader not initialized'):
            dst.initialize_writer()
            src.read_into(dst)

        src.remove()
        dst.remove()

    def test_validate_length(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        backend.write(EXAMPLE_DATA)
        backend.close()

        assert backend.validate_length(len(EXAMPLE_DATA)) is True
        assert backend.validate_length(len(EXAMPLE_DATA) + 1) is False
        assert backend.validate_length(len(EXAMPLE_DATA) - 1) is False
        backend.remove()

    def test_resume_append(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        backend.write(b'AAA')
        backend.close()

        # reopen in resume mode (append)
        backend.initialize_writer(resume=True)
        backend.write(b'BBB')
        backend.close()

        backend.initialize_reader()
        data = backend.reader.read()
        assert data == b'AAABBB'
        backend.close()
        backend.remove()

    def test_resume_new_file(self, fd, filename, backend_cls):
        # Should handle resuming if file does not exist (i.e. treat as new file)
        backend = backend_cls(fd, filename)
        backend.initialize_writer(resume=True)
        backend.write(b'AAA')
        backend.close()

        backend.initialize_reader()
        data = backend.reader.read()
        assert data == b'AAA'
        backend.close()
        backend.remove()

    def test_no_resume_overwrite(self, fd, filename, backend_cls):
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        backend.write(b'AAA')
        backend.close()

        # reopen without resume should overwrite
        backend.initialize_writer(resume=False)
        backend.write(b'BBB')
        backend.close()

        backend.initialize_reader()
        data = backend.reader.read()
        assert data == b'BBB'
        backend.close()
        backend.remove()

    def test_close_flushes(self, fd, filename, backend_cls):
        # On close, should call fp.flush() before closing to ensure all data is written
        backend = backend_cls(fd, filename)
        backend.initialize_writer()
        backend.write(EXAMPLE_DATA)

        original_flush = backend.writer.flush
        mock = MagicMock()
        mock.side_effect = original_flush
        backend.writer.flush = mock

        mock.assert_not_called()
        backend.close()
        mock.assert_called()
        backend.remove()

    def test_write_flushes(self, fd, filename, backend_cls):
        # When writing data, should call flush to ensure data is written
        backend = backend_cls(fd, filename)
        backend.initialize_writer()

        original_flush = backend.writer.flush
        mock = MagicMock()
        mock.side_effect = original_flush
        backend.writer.flush = mock

        backend.write(EXAMPLE_DATA)
        mock.assert_called()
        backend.close()
        backend.remove()


class TestDiskFormatIOBackend:

    def test_disk_write_read(self, fd, filename, tmp_path):
        # Should write a file to the disk
        backend = DiskFormatIOBackend(fd, filename)
        assert backend.exists() is False
        backend.initialize_writer()
        written = backend.write(EXAMPLE_DATA)
        assert written == len(EXAMPLE_DATA)
        backend.close()

        assert backend.exists() is True
        assert os.path.exists(filename)
        assert os.path.getsize(filename) == len(EXAMPLE_DATA)

        backend.initialize_reader()
        data = backend.reader.read()
        assert data == EXAMPLE_DATA
        backend.close()

        backend.remove()
        assert backend.exists() is False
        assert not os.path.exists(filename)

    def test_disk_file_not_exists(self, fd, filename):
        backend = DiskFormatIOBackend(fd, filename)
        assert backend.exists() is False

        with pytest.raises(FileNotFoundError):
            backend.initialize_reader()


class TestMemoryFormatIOBackend:
    def test_memory_nonclosing_writer_does_not_close_underlying_store(self, fd, filename):
        backend = MemoryFormatIOBackend(fd, filename)
        backend.initialize_writer()
        backend.write(EXAMPLE_DATA)
        backend.close()

        # The NonClosingBufferedWriter should not close the underlying BytesIO
        assert hasattr(backend, '_memory_store')
        assert isinstance(backend._memory_store, io.BytesIO)
        assert backend._memory_store.closed is False

        # Data should still be present in the memory store
        assert backend._memory_store.getbuffer().nbytes == len(EXAMPLE_DATA)

        # We can create a reader and read the same data
        backend.initialize_reader()
        assert backend.reader.read() == EXAMPLE_DATA
        backend.close()

        # We can create a new writer to write new data
        backend.initialize_writer()
        new_data = b'xyz' * 5
        backend.write(new_data)
        backend.close()
        assert backend._memory_store.closed is False

        backend.initialize_reader()
        assert backend.reader.read() == new_data
        backend.close()
        assert backend._memory_store.closed is False

        backend.remove()
