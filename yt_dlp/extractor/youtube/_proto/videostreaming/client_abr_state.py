from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class ClientAbrState:
    player_time_ms: protobug.Int64 | None = protobug.field(28, default=None)
    enabled_track_types_bitfield: protobug.Int32 | None = protobug.field(40, default=None)
