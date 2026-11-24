from __future__ import annotations

from yt_dlp.dependencies import protobug
from yt_dlp.extractor.youtube._proto.videostreaming.time_range import TimeRange


class TrackType(protobug.Enum, strict=False):
    AUDIO = 1
    VIDEO = 2


class CuepointEvent(protobug.Enum, strict=False):
    UNKNOWN = 0
    START = 1
    CONTINUE = 2
    STOP = 3
    INSERTION = 4
    PREDICT_START = 5


class CuepointType(protobug.Enum, strict=False):
    UNKNOWN = 0
    AD = 1
    SLATE = 2


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
class CuepointInfo:
    cuepoint: Cuepoint | None = protobug.field(1, default=None)
    track_type: TrackType | None = protobug.field(2, default=None)
    sequence_number: protobug.Int32 | None = protobug.field(3, default=None)
    time_range: TimeRange | None = protobug.field(4, default=None)
    tile_context: protobug.String | None = protobug.field(5, default=None)


@protobug.message
class CuepointList:
    cuepoint_info: list[CuepointInfo] = protobug.field(1, default_factory=list)
