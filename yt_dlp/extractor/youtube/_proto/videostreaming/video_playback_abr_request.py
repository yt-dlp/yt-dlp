from __future__ import annotations

from yt_dlp.dependencies import protobug

from .buffered_range import BufferedRange
from .client_abr_state import ClientAbrState
from .format_id import FormatId
from .streamer_context import StreamerContext


@protobug.message
class VideoPlaybackAbrRequest:
    client_abr_state: ClientAbrState = protobug.field(1, default=None)
    initialized_format_ids: list[FormatId] = protobug.field(2, default_factory=list)
    buffered_ranges: list[BufferedRange] = protobug.field(3, default_factory=list)
    player_time_ms: protobug.Int64 | None = protobug.field(4, default=None)
    video_playback_ustreamer_config: protobug.Bytes | None = protobug.field(5, default=None)

    selected_audio_format_ids: list[FormatId] = protobug.field(16, default_factory=list)
    selected_video_format_ids: list[FormatId] = protobug.field(17, default_factory=list)
    selected_caption_format_ids: list[FormatId] = protobug.field(18, default_factory=list)
    streamer_context: StreamerContext = protobug.field(19, default_factory=StreamerContext)
