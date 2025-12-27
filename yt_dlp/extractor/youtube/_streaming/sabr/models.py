from __future__ import annotations

import dataclasses

from yt_dlp.extractor.youtube._proto.videostreaming import FormatId
from yt_dlp.extractor.youtube.pot._provider import IEContentProviderLogger


@dataclasses.dataclass
class Segment:
    format_id: FormatId
    is_init_segment: bool = False
    duration_ms: int = 0
    start_ms: int = 0
    start_data_range: int = 0
    sequence_number: int | None = 0
    content_length: int | None = None
    content_length_estimated: bool = False
    initialized_format: InitializedFormat = None
    # Whether duration_ms is an estimate
    duration_estimated: bool = False
    # Whether we should discard the segment data
    discard: bool = False
    # Whether the segment has already been consumed.
    # `discard` should be set to True if this is the case.
    consumed: bool = False
    received_data_length: int = 0
    sequence_lmt: int | None = None


@dataclasses.dataclass
class ConsumedRange:
    start_sequence_number: int
    end_sequence_number: int
    start_time_ms: int
    duration_ms: int


@dataclasses.dataclass
class InitializedFormat:
    format_id: FormatId
    video_id: str
    format_selector: FormatSelector | None = None
    duration_ms: int = 0
    end_time_ms: int = 0
    mime_type: str = None
    # Current segment in the sequence. Set to None to break the sequence and allow a seek.
    current_segment: Segment | None = None
    init_segment: Segment | None | bool = None
    consumed_ranges: list[ConsumedRange] = dataclasses.field(default_factory=list)
    total_segments: int = None
    # Whether we should discard any data received for this format
    discard: bool = False
    sequence_lmt: int | None = None


SabrLogger = IEContentProviderLogger


@dataclasses.dataclass
class FormatSelector:
    display_name: str
    format_ids: list[FormatId] = dataclasses.field(default_factory=list)
    discard_media: bool = False
    mime_prefix: str | None = None

    def match(self, format_id: FormatId = None, mime_type: str | None = None, **kwargs) -> bool:
        return (
            format_id in self.format_ids
            or (
                not self.format_ids
                and self.mime_prefix
                and mime_type and mime_type.lower().startswith(self.mime_prefix)
            )
        )


@dataclasses.dataclass
class AudioSelector(FormatSelector):
    mime_prefix: str = dataclasses.field(default='audio')


@dataclasses.dataclass
class VideoSelector(FormatSelector):
    mime_prefix: str = dataclasses.field(default='video')


@dataclasses.dataclass
class CaptionSelector(FormatSelector):
    mime_prefix: str = dataclasses.field(default='text')
