from __future__ import annotations

import dataclasses
from yt_dlp.utils import DownloadError
from ._io import DiskFormatIOBackend, MemoryFormatIOBackend


@dataclasses.dataclass
class Segment:
    segment_id: str
    content_length: int | None = None
    content_length_estimated: bool = False
    sequence_number: int | None = None
    start_time_ms: int | None = None
    duration_ms: int | None = None
    duration_estimated: bool = False
    is_init_segment: bool = False


@dataclasses.dataclass
class Sequence:
    sequence_id: str
    # The segments may not have a start byte range, so to keep it simple we will track
    # length of the sequence. We can infer from this and the segment's content_length where they should end and begin.
    sequence_content_length: int = 0
    first_segment: Segment | None = None
    last_segment: Segment | None = None


class SequenceFile:

    def __init__(self, fd, format_filename, sequence: Sequence, resume=False):
        self.fd = fd
        self.format_filename = format_filename
        self.sequence = sequence
        self.file = DiskFormatIOBackend(
            fd=self.fd,
            filename=self.format_filename + f'.sq{self.sequence_id}.sabr.part',
        )
        self.current_segment: SegmentFile | None = None
        self.resume = resume

        sequence_file_exists = self.file.exists()

        if not resume and sequence_file_exists:
            self.file.remove()

        elif not self.sequence.last_segment and sequence_file_exists:
            self.file.remove()

        if self.sequence.last_segment and not sequence_file_exists:
            raise DownloadError(f'Cannot find existing sequence {self.sequence_id} file')

        if self.sequence.last_segment and not self.file.validate_length(self.sequence.sequence_content_length):
            self.file.remove()
            raise DownloadError(f'Existing sequence {self.sequence_id} file is not valid; removing')

    @property
    def sequence_id(self):
        return self.sequence.sequence_id

    @property
    def current_length(self):
        total = self.sequence.sequence_content_length
        if self.current_segment:
            total += self.current_segment.current_length
        return total

    def is_next_segment(self, segment: Segment):
        if self.current_segment:
            return False
        latest_segment = self.sequence.last_segment or self.sequence.first_segment
        if not latest_segment:
            return True
        if segment.is_init_segment and latest_segment.is_init_segment:
            # Only one segment allowed for init segments
            return False
        return segment.sequence_number == latest_segment.sequence_number + 1

    def is_current_segment(self, segment_id: str):
        if not self.current_segment:
            return False
        return self.current_segment.segment_id == segment_id

    def initialize_segment(self, segment: Segment):
        if self.current_segment and not self.is_current_segment(segment.segment_id):
            raise ValueError('Cannot reinitialize a segment that does not match the current segment')

        if not self.current_segment and not self.is_next_segment(segment):
            raise ValueError('Cannot initialize a segment that does not match the next segment')

        self.current_segment = SegmentFile(
            fd=self.fd,
            format_filename=self.format_filename,
            segment=segment,
        )

    def write_segment_data(self, data, segment_id: str):
        if not self.is_current_segment(segment_id):
            raise ValueError('Cannot write to a segment that does not match the current segment')

        self.current_segment.write(data)

    def end_segment(self, segment_id):
        if not self.is_current_segment(segment_id):
            raise ValueError('Cannot end a segment that does not exist')

        self.current_segment.finish_write()

        if (
            self.current_segment.segment.content_length
            and not self.current_segment.segment.content_length_estimated
            and self.current_segment.current_length != self.current_segment.segment.content_length
        ):
            raise DownloadError(
                f'Filesize mismatch for segment {self.current_segment.segment_id}: '
                f'Expected {self.current_segment.segment.content_length} bytes, got {self.current_segment.current_length} bytes')

        self.current_segment.segment.content_length = self.current_segment.current_length
        self.current_segment.segment.content_length_estimated = False

        if not self.sequence.first_segment:
            self.sequence.first_segment = self.current_segment.segment

        self.sequence.last_segment = self.current_segment.segment
        self.sequence.sequence_content_length += self.current_segment.current_length

        if not self.file.mode:
            self.file.initialize_writer(self.resume)

        self.current_segment.read_into(self.file)
        self.current_segment.remove()
        self.current_segment = None

    def read_into(self, backend):
        self.file.initialize_reader()
        self.file.read_into(backend)
        self.file.close()

    def remove(self):
        self.close()
        self.file.remove()

    def close(self):
        self.file.close()


class SegmentFile:

    def __init__(self, fd, format_filename, segment: Segment, memory_file_limit=2 * 1024 * 1024):
        self.fd = fd
        self.format_filename = format_filename
        self.segment: Segment = segment
        self.current_length = 0

        filename = format_filename + f'.sg{segment.sequence_number}.sabr.part'
        # Store the segment in memory if it is small enough
        if segment.content_length and segment.content_length <= memory_file_limit:
            self.file = MemoryFormatIOBackend(
                fd=self.fd,
                filename=filename,
            )
        else:
            self.file = DiskFormatIOBackend(
                fd=self.fd,
                filename=filename,
            )

        # Never resume a segment
        exists = self.file.exists()
        if exists:
            self.file.remove()

    @property
    def segment_id(self):
        return self.segment.segment_id

    def write(self, data):
        if not self.file.mode:
            self.file.initialize_writer(resume=False)
        self.current_length += self.file.write(data)

    def read_into(self, file):
        self.file.initialize_reader()
        self.file.read_into(file)
        self.file.close()

    def remove(self):
        self.close()
        self.file.remove()

    def finish_write(self):
        self.close()

    def close(self):
        self.file.close()
