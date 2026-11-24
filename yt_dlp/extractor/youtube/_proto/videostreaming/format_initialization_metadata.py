from __future__ import annotations

from yt_dlp.dependencies import protobug

from .format_id import FormatId
from ..innertube import Range


@protobug.message
class FormatInitializationMetadata:
    video_id: protobug.String = protobug.field(1, default=None)
    format_id: FormatId = protobug.field(2, default=None)
    end_time_ms: protobug.Int32 | None = protobug.field(3, default=None)
    total_segments: protobug.Int32 | None = protobug.field(4, default=None)
    mime_type: protobug.String | None = protobug.field(5, default=None)
    init_range: Range | None = protobug.field(6, default=None)
    index_range: Range | None = protobug.field(7, default=None)
    duration_ticks: protobug.Int32 | None = protobug.field(9, default=None)
    duration_timescale: protobug.Int32 | None = protobug.field(10, default=None)
