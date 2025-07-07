from __future__ import annotations

import dataclasses
import enum

from yt_dlp.extractor.youtube._proto.videostreaming import FormatId

from .models import FormatSelector


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


@dataclasses.dataclass
class MediaSegmentDataSabrPart(SabrPart):
    format_selector: FormatSelector
    format_id: FormatId
    sequence_number: int | None = None
    is_init_segment: bool = False
    total_segments: int = None
    data: bytes = b''
    content_length: int = None
    segment_start_bytes: int = None


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
    class PoTokenStatus(enum.Enum):
        OK = enum.auto()                          # PO Token is provided and valid
        MISSING = enum.auto()                     # PO Token is not provided, and is required. A PO Token should be provided ASAP
        INVALID = enum.auto()                     # PO Token is provided, but is invalid. A new one should be generated ASAP
        PENDING = enum.auto()                     # PO Token is provided, but probably only a cold start token. A full PO Token should be provided ASAP
        NOT_REQUIRED = enum.auto()                # PO Token is not provided, and is not required
        PENDING_MISSING = enum.auto()             # PO Token is not provided, but is pending. A full PO Token should be (probably) provided ASAP

    status: PoTokenStatus


@dataclasses.dataclass
class RefreshPlayerResponseSabrPart(SabrPart):

    class Reason(enum.Enum):
        UNKNOWN = enum.auto()
        SABR_URL_EXPIRY = enum.auto()
        SABR_RELOAD_PLAYER_RESPONSE = enum.auto()

    reason: Reason
    reload_playback_token: str = None


@dataclasses.dataclass
class MediaSeekSabrPart(SabrPart):
    # Lets the consumer know the media sequence for a format may change
    class Reason(enum.Enum):
        UNKNOWN = enum.auto()
        SERVER_SEEK = enum.auto()  # SABR_SEEK from server
        CONSUMED_SEEK = enum.auto()  # Seeking as next fragment is already buffered

    reason: Reason
    format_id: FormatId
    format_selector: FormatSelector
