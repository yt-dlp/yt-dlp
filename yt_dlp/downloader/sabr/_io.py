from __future__ import annotations
import abc
import io
import os
import shutil
import typing


class FormatIOBackend(abc.ABC):
    def __init__(self, fd, filename, buffer=1024 * 1024):
        self.fd = fd
        self.filename = filename
        self.write_buffer = buffer
        self._fp = None
        self._fp_mode = None

    @property
    def writer(self):
        if self._fp is None or self._fp_mode != 'write':
            return None
        return self._fp

    @property
    def reader(self):
        if self._fp is None or self._fp_mode != 'read':
            return None
        return self._fp

    def initialize_writer(self, resume=False):
        if self._fp is not None:
            raise ValueError('Backend already initialized')

        self._fp = self._create_writer(resume)
        self._fp_mode = 'write'

    @abc.abstractmethod
    def _create_writer(self, resume=False) -> typing.IO:
        pass

    def initialize_reader(self):
        if self._fp is not None:
            raise ValueError('Backend already initialized')
        self._fp = self._create_reader()
        self._fp_mode = 'read'

    @abc.abstractmethod
    def _create_reader(self) -> typing.IO:
        pass

    def close(self):
        if self._fp and not self._fp.closed:
            self._fp.flush()
            self._fp.close()
        self._fp = None
        self._fp_mode = None

    @abc.abstractmethod
    def validate_length(self, expected_length):
        pass

    def remove(self):
        self.close()
        self._remove()

    @abc.abstractmethod
    def _remove(self):
        pass

    @abc.abstractmethod
    def exists(self):
        pass

    @property
    def mode(self):
        if self._fp is None:
            return None
        return self._fp_mode

    def write(self, data: io.BufferedIOBase | bytes):
        if not self.writer:
            raise ValueError('Backend writer not initialized')

        if isinstance(data, bytes):
            bytes_written = self.writer.write(data)
        elif isinstance(data, io.BufferedIOBase):
            bytes_written = self.writer.tell()
            shutil.copyfileobj(data, self.writer, length=self.write_buffer)
            bytes_written = self.writer.tell() - bytes_written
        else:
            raise TypeError('Data must be bytes or a BufferedIOBase object')

        self.writer.flush()

        return bytes_written

    def read_into(self, backend):
        if not backend.writer:
            raise ValueError('Backend writer not initialized')
        if not self.reader:
            raise ValueError('Backend reader not initialized')
        shutil.copyfileobj(self.reader, backend.writer, length=self.write_buffer)
        backend.writer.flush()


class DiskFormatIOBackend(FormatIOBackend):
    def _create_writer(self, resume=False) -> typing.IO:
        if resume and self.exists():
            write_fp, self.filename = self.fd.sanitize_open(self.filename, 'ab')
        else:
            write_fp, self.filename = self.fd.sanitize_open(self.filename, 'wb')
        return write_fp

    def _create_reader(self) -> typing.IO:
        read_fp, self.filename = self.fd.sanitize_open(self.filename, 'rb')
        return read_fp

    def validate_length(self, expected_length):
        return os.path.getsize(self.filename) == expected_length

    def _remove(self):
        self.fd.try_remove(self.filename)

    def exists(self):
        return os.path.isfile(self.filename)


class MemoryFormatIOBackend(FormatIOBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._memory_store = io.BytesIO()

    def _create_writer(self, resume=False) -> typing.IO:
        class NonClosingBufferedWriter(io.BufferedWriter):
            def close(self):
                self.flush()
                # Do not close the underlying buffer

        if resume and self.exists():
            self._memory_store.seek(0, io.SEEK_END)
        else:
            self._memory_store.seek(0)
            self._memory_store.truncate(0)

        return NonClosingBufferedWriter(self._memory_store)

    def _create_reader(self) -> typing.IO:
        class NonClosingBufferedReader(io.BufferedReader):
            def close(self):
                self.flush()

        # Seek to the beginning of the buffer
        self._memory_store.seek(0)
        return NonClosingBufferedReader(self._memory_store)

    def validate_length(self, expected_length):
        return self._memory_store.getbuffer().nbytes != expected_length

    def _remove(self):
        self._memory_store = io.BytesIO()

    def exists(self):
        return self._memory_store.getbuffer().nbytes > 0
