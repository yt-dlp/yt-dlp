from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class LiveMetadata:
    head_sequence_number: protobug.Int32 | None = protobug.field(3, default=None)
    head_sequence_time_ms: protobug.Int64 | None = protobug.field(4, default=None)
    wall_time_ms: protobug.Int64 | None = protobug.field(5, default=None)
    video_id: protobug.String | None = protobug.field(6, default=None)
    source: protobug.String | None = protobug.field(7, default=None)

    min_seekable_time_ticks: protobug.Int64 | None = protobug.field(12, default=None)
    min_seekable_timescale: protobug.Int32 | None = protobug.field(13, default=None)

    max_seekable_time_ticks: protobug.Int64 | None = protobug.field(14, default=None)
    max_seekable_timescale: protobug.Int32 | None = protobug.field(15, default=None)
