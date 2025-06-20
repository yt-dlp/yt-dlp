from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class Range:
    start: protobug.Int64 | None = protobug.field(1, default=None)
    end: protobug.Int64 | None = protobug.field(2, default=None)
