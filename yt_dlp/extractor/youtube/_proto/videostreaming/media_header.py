from __future__ import annotations

from yt_dlp.dependencies import protobug

from .format_id import FormatId
from .time_range import TimeRange
from ..innertube import CompressionAlgorithm


@protobug.message
class MediaHeader:
    header_id: protobug.UInt32 | None = protobug.field(1, default=None)
    video_id: protobug.String | None = protobug.field(2, default=None)
    itag: protobug.Int32 | None = protobug.field(3, default=None)
    last_modified: protobug.UInt64 | None = protobug.field(4, default=None)
    xtags: protobug.String | None = protobug.field(5, default=None)
    start_data_range: protobug.Int32 | None = protobug.field(6, default=None)
    compression: CompressionAlgorithm | None = protobug.field(7, default=None)
    is_init_segment: protobug.Bool | None = protobug.field(8, default=None)
    sequence_number: protobug.Int64 | None = protobug.field(9, default=None)
    bitrate_bps: protobug.Int64 | None = protobug.field(10, default=None)
    start_ms: protobug.Int32 | None = protobug.field(11, default=None)
    duration_ms: protobug.Int32 | None = protobug.field(12, default=None)
    format_id: FormatId | None = protobug.field(13, default=None)
    content_length: protobug.Int64 | None = protobug.field(14, default=None)
    time_range: TimeRange | None = protobug.field(15, default=None)
    sequence_lmt: protobug.Int32 | None = protobug.field(16, default=None)
