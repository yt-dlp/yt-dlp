from __future__ import annotations

import dataclasses
import enum
import typing
from io import BufferedIOBase

from yt_dlp.extractor.youtube._proto.videostreaming import FormatId

from .models import FormatSelector, PoTokenStatus


@dataclasses.dataclass
class SabrPart:
    pass


@dataclasses.dataclass
class MediaSegmentInitSabrPart(SabrPart):
    format_selector: FormatSelector
    format_id: FormatId
    sequence_number: int | None = None
    is_init_segment: bool = False
    total_segments: int = None
    start_time_ms: int = None
    player_time_ms: int = None
    duration_ms: int = None
    duration_estimated: bool = False
    start_bytes: int = None
    content_length: int = None
    content_length_estimated: bool = False
    register_data_callback: typing.Callable[[typing.Callable[[MediaSegmentDataSabrPart], None]], None] | None = None


@dataclasses.dataclass
class MediaSegmentDataSabrPart(SabrPart):
    format_selector: FormatSelector
    format_id: FormatId
    sequence_number: int | None = None
    is_init_segment: bool = False
    total_segments: int | None = None
    data: bytes | BufferedIOBase = b''
    content_length: int | None = None
    segment_start_bytes: int | None = None


@dataclasses.dataclass
class MediaSegmentEndSabrPart(SabrPart):
    format_selector: FormatSelector
    format_id: FormatId
    sequence_number: int | None = None
    is_init_segment: bool = False
    total_segments: int = None


@dataclasses.dataclass
class FormatInitializedSabrPart(SabrPart):
    format_id: FormatId
    format_selector: FormatSelector


@dataclasses.dataclass
class PoTokenStatusSabrPart(SabrPart):
    status: PoTokenStatus


@dataclasses.dataclass
class MediaSeekSabrPart(SabrPart):
    # Lets the consumer know the media sequence for a format may change
    class Reason(enum.Enum):
        UNKNOWN = enum.auto()
        SERVER_SEEK = enum.auto()  # SABR_SEEK from server

    reason: Reason
    format_id: FormatId
    format_selector: FormatSelector


@dataclasses.dataclass
class BroadcastStateSabrPart(SabrPart):
    available_dvr_window_ms: int
    full_stream_available: bool
