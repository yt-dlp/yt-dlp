from __future__ import annotations

from yt_dlp.dependencies import protobug


@protobug.message
class NextRequestPolicy:
    target_audio_readahead_ms: protobug.Int32 | None = protobug.field(1, default=None)
    target_video_readahead_ms: protobug.Int32 | None = protobug.field(2, default=None)
    max_time_since_last_request_ms: protobug.Int32 | None = protobug.field(3, default=None)
    backoff_time_ms: protobug.Int32 | None = protobug.field(4, default=None)
    min_audio_readahead_ms: protobug.Int32 | None = protobug.field(5, default=None)
    min_video_readahead_ms: protobug.Int32 | None = protobug.field(6, default=None)
    playback_cookie: protobug.Bytes | None = protobug.field(7, default=None)
    video_id: protobug.String | None = protobug.field(8, default=None)
