from __future__ import annotations

from yt_dlp.dependencies import protobug

from .format_id import FormatId
from .time_range import TimeRange


@protobug.message
class BufferedRange:
    format_id: FormatId | None = protobug.field(1, default=None)
    start_time_ms: protobug.Int64 | None = protobug.field(2, default=None)
    duration_ms: protobug.Int64 | None = protobug.field(3, default=None)
    start_segment_index: protobug.Int32 | None = protobug.field(4, default=None)
    end_segment_index: protobug.Int32 | None = protobug.field(5, default=None)
    time_range: TimeRange | None = protobug.field(6, default=None)
