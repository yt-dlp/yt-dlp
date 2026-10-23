from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class TimeRange:
    start_ticks: protobug.Int64 | None = protobug.field(1, default=None)
    duration_ticks: protobug.Int64 | None = protobug.field(2, default=None)
    timescale: protobug.Int32 | None = protobug.field(3, default=None)
