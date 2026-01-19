from __future__ import annotations
import contextlib
import os
import tempfile

from yt_dlp.dependencies import protobug
from yt_dlp.extractor.youtube._proto.videostreaming import FormatId


@protobug.message
class SabrStateSegment:
    sequence_number: protobug.Int32 = protobug.field(1)
    start_time_ms: protobug.Int64 = protobug.field(2)
    duration_ms: protobug.Int64 = protobug.field(3)
    duration_estimated: protobug.Bool = protobug.field(4)
    content_length: protobug.Int64 = protobug.field(5)


@protobug.message
class SabrStateSequence:
    sequence_start_number: protobug.Int32 = protobug.field(1)
    sequence_content_length: protobug.Int64 = protobug.field(2)
    first_segment: SabrStateSegment = protobug.field(3)
    last_segment: SabrStateSegment = protobug.field(4)


@protobug.message
class SabrStateInitSegment:
    content_length: protobug.Int64 = protobug.field(2)


@protobug.message
class SabrState:
    format_id: FormatId = protobug.field(1)
    init_segment: SabrStateInitSegment | None = protobug.field(2, default=None)
    sequences: list[SabrStateSequence] = protobug.field(3, default_factory=list)


class SabrStateFile:

    def __init__(self, format_filename, fd):
        self.filename = format_filename + '.sabr.state'
        self.fd = fd

    @property
    def exists(self):
        return os.path.isfile(self.filename)

    def retrieve(self):
        stream, self.filename = self.fd.sanitize_open(self.filename, 'rb')
        try:
            return self.deserialize(stream.read())
        finally:
            stream.close()

    def update(self, sabr_document):
        # Attempt to write progress document somewhat atomically to avoid corruption
        with tempfile.NamedTemporaryFile('wb', delete=False, dir=os.path.dirname(self.filename)) as tf:
            tf.write(self.serialize(sabr_document))
            tf.flush()
            os.fsync(tf.fileno())

        try:
            os.replace(tf.name, self.filename)
        finally:
            if os.path.exists(tf.name):
                with contextlib.suppress(FileNotFoundError, OSError):
                    os.unlink(tf.name)

    def serialize(self, sabr_document):
        return protobug.dumps(sabr_document)

    def deserialize(self, data):
        return protobug.loads(data, SabrState)

    def remove(self):
        self.fd.try_remove(self.filename)
