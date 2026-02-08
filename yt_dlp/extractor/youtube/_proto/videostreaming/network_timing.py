from __future__ import annotations

from yt_dlp.dependencies import protobug
from yt_dlp.extractor.youtube._proto.videostreaming import TimeRange


class TrackType(protobug.Enum, strict=False):
    TRACK_TYPE_AUDIO = 1
    TRACK_TYPE_VIDEO = 2


class CuepointEvent(protobug.Enum, strict=False):
    CUEPOINT_EVENT_UNKNOWN = 0
    CUEPOINT_EVENT_START = 1
    CUEPOINT_EVENT_CONTINUE = 2
    CUEPOINT_EVENT_STOP = 3
    CUEPOINT_EVENT_INSERTION = 4
    CUEPOINT_EVENT_PREDICT_START = 5


class CuepointType(protobug.Enum, strict=False):
    CUEPOINT_TYPE_UNKNOWN = 0
    CUEPOINT_TYPE_AD = 1
    CUEPOINT_TYPE_SLATE = 2


@protobug.message
class Cuepoint:
    type: CuepointType | None = protobug.field(1, default=None)
    event: CuepointEvent | None = protobug.field(2, default=None)
    duration_sec: protobug.Double | None = protobug.field(3, default=None)
    offset_sec: protobug.Double | None = protobug.field(4, default=None)
    context: protobug.String | None = protobug.field(5, default=None)
    identifier: protobug.String | None = protobug.field(6, default=None)
    unknown_int_9: protobug.Int32 | None = protobug.field(9, default=None)


@protobug.message
class Timing:
    cuepoint: Cuepoint | None = protobug.field(1, default=None)
    track_type: TrackType | None = protobug.field(2, default=None)
    sequence_number: protobug.Int32 | None = protobug.field(3, default=None)
    time_range: TimeRange | None = protobug.field(4, default=None)
    tile_context: protobug.String | None = protobug.field(5, default=None)


@protobug.message
class NetworkTiming:
    timings: list[Timing] = protobug.field(1, default_factory=list)
