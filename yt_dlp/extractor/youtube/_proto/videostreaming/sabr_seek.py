from __future__ import annotations

from yt_dlp.dependencies import protobug

from ..innertube import SeekSource


@protobug.message
class SabrSeek:
    seek_time_ticks: protobug.Int32 = protobug.field(1)
    timescale: protobug.Int32 = protobug.field(2)
    seek_source: SeekSource | None = protobug.field(3, default=None)
