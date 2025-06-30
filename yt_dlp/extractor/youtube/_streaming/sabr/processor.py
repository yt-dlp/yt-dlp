from __future__ import annotations

import base64
import io
import math

from yt_dlp.extractor.youtube._proto.innertube import ClientInfo, NextRequestPolicy
from yt_dlp.extractor.youtube._proto.videostreaming import (
    BufferedRange,
    ClientAbrState,
    FormatInitializationMetadata,
    LiveMetadata,
    MediaHeader,
    SabrContext,
    SabrContextSendingPolicy,
    SabrContextUpdate,
    SabrSeek,
    StreamerContext,
    StreamProtectionStatus,
    TimeRange,
    VideoPlaybackAbrRequest,
)

from .exceptions import MediaSegmentMismatchError, SabrStreamError
from .models import (
    AudioSelector,
    CaptionSelector,
    ConsumedRange,
    InitializedFormat,
    SabrLogger,
    Segment,
    VideoSelector,
)
from .part import (
    FormatInitializedSabrPart,
    MediaSeekSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
    MediaSegmentInitSabrPart,
    PoTokenStatusSabrPart,
)
from .utils import ticks_to_ms


class ProcessMediaEndResult:
    def __init__(self, sabr_part: MediaSegmentEndSabrPart = None, is_new_segment: bool = False):
        self.is_new_segment = is_new_segment
        self.sabr_part = sabr_part


class ProcessMediaResult:
    def __init__(self, sabr_part: MediaSegmentDataSabrPart = None):
        self.sabr_part = sabr_part


class ProcessMediaHeaderResult:
    def __init__(self, sabr_part: MediaSegmentInitSabrPart | None = None):
        self.sabr_part = sabr_part


class ProcessLiveMetadataResult:
    def __init__(self, seek_sabr_parts: list[MediaSeekSabrPart] | None = None):
        self.seek_sabr_parts = seek_sabr_parts or []


class ProcessStreamProtectionStatusResult:
    def __init__(self, sabr_part: PoTokenStatusSabrPart | None = None):
        self.sabr_part = sabr_part


class ProcessFormatInitializationMetadataResult:
    def __init__(self, sabr_part: FormatInitializedSabrPart | None = None):
        self.sabr_part = sabr_part


class ProcessSabrSeekResult:
    def __init__(self, seek_sabr_parts: list[MediaSeekSabrPart] | None = None):
        self.seek_sabr_parts = seek_sabr_parts or []


class SabrProcessor:
    """
    SABR Processor

    This handles core SABR protocol logic, independent of requests.
    """

    def __init__(
        self,
        logger: SabrLogger,
        video_playback_ustreamer_config: str,
        client_info: ClientInfo,
        audio_selection: AudioSelector | None = None,
        video_selection: VideoSelector | None = None,
        caption_selection: CaptionSelector | None = None,
        live_segment_target_duration_sec: int | None = None,
        live_segment_target_duration_tolerance_ms: int | None = None,
        start_time_ms: int | None = None,
        po_token: str | None = None,
        post_live: bool = False,
        video_id: str | None = None,
    ):

        self.logger = logger

        self.video_playback_ustreamer_config = video_playback_ustreamer_config
        self.po_token = po_token
        self.client_info = client_info
        self.live_segment_target_duration_sec = live_segment_target_duration_sec or 5
        self.live_segment_target_duration_tolerance_ms = live_segment_target_duration_tolerance_ms or 100
        if self.live_segment_target_duration_tolerance_ms >= (self.live_segment_target_duration_sec * 1000) / 2:
            raise ValueError(
                'live_segment_target_duration_tolerance_ms must be less than '
                'half of live_segment_target_duration_sec in milliseconds',
            )
        self.start_time_ms = start_time_ms or 0
        if self.start_time_ms < 0:
            raise ValueError('start_time_ms must be greater than or equal to 0')

        self.post_live = post_live
        self._is_live = False
        self.video_id = video_id

        self._audio_format_selector = audio_selection
        self._video_format_selector = video_selection
        self._caption_format_selector = caption_selection

        # IMPORTANT: initialized formats is assumed to contain only ACTIVE formats
        self.initialized_formats: dict[str, InitializedFormat] = {}
        self.stream_protection_status: StreamProtectionStatus.Status | None = None

        self.partial_segments: dict[int, Segment] = {}
        self.total_duration_ms = None
        self.selected_audio_format_ids = []
        self.selected_video_format_ids = []
        self.selected_caption_format_ids = []
        self.next_request_policy: NextRequestPolicy | None = None
        self.live_metadata: LiveMetadata | None = None
        self.client_abr_state: ClientAbrState
        self.sabr_contexts_to_send: set[int] = set()
        self.sabr_context_updates: dict[int, SabrContextUpdate] = {}
        self._initialize_cabr_state()

    @property
    def is_live(self):
        return bool(
            self.live_metadata
            or self._is_live,
        )

    @is_live.setter
    def is_live(self, value: bool):
        self._is_live = value

    def _initialize_cabr_state(self):
        # SABR supports: audio+video, audio+video+captions or audio-only.
        # For the other cases, we'll mark the tracks to be discarded (and fully buffered on initialization)

        if not self._video_format_selector:
            self._video_format_selector = VideoSelector(display_name='video_ignore', discard_media=True)

        if not self._audio_format_selector:
            self._audio_format_selector = AudioSelector(display_name='audio_ignore', discard_media=True)

        if not self._caption_format_selector:
            self._caption_format_selector = CaptionSelector(display_name='caption_ignore', discard_media=True)

        enabled_track_types_bitfield = 0  # Audio+Video

        if self._video_format_selector.discard_media:
            enabled_track_types_bitfield = 1  # Audio only

        if not self._caption_format_selector.discard_media:
            # SABR does not support caption-only or audio+captions only - can only get audio+video with captions
            # If audio or video is not selected, the tracks will be initialized but marked as buffered.
            enabled_track_types_bitfield = 7

        self.selected_audio_format_ids = self._audio_format_selector.format_ids
        self.selected_video_format_ids = self._video_format_selector.format_ids
        self.selected_caption_format_ids = self._caption_format_selector.format_ids

        self.logger.debug(f'Starting playback at: {self.start_time_ms}ms')
        self.client_abr_state = ClientAbrState(
            player_time_ms=self.start_time_ms,
            enabled_track_types_bitfield=enabled_track_types_bitfield)

    def match_format_selector(self, format_init_metadata):
        for format_selector in (self._video_format_selector, self._audio_format_selector, self._caption_format_selector):
            if not format_selector:
                continue
            if format_selector.match(format_id=format_init_metadata.format_id, mime_type=format_init_metadata.mime_type):
                return format_selector
        return None

    def process_media_header(self, media_header: MediaHeader) -> ProcessMediaHeaderResult:
        if media_header.video_id and self.video_id and media_header.video_id != self.video_id:
            raise SabrStreamError(
                f'Received unexpected MediaHeader for video'
                f' {media_header.video_id} (expecting {self.video_id})')

        if not media_header.format_id:
            raise SabrStreamError(f'Format ID not found in MediaHeader (media_header={media_header})')

        # Guard. This should not happen, except if we don't clear partial segments
        if media_header.header_id in self.partial_segments:
            raise SabrStreamError(f'Header ID {media_header.header_id} already exists')

        result = ProcessMediaHeaderResult()

        initialized_format = self.initialized_formats.get(str(media_header.format_id))
        if not initialized_format:
            self.logger.debug(f'Initialized format not found for {media_header.format_id}')
            return result

        if media_header.compression:
            # Unknown when this is used, but it is not supported currently
            raise SabrStreamError(f'Compression not supported in MediaHeader (media_header={media_header})')

        sequence_number, is_init_segment = media_header.sequence_number, media_header.is_init_segment
        if sequence_number is None and not media_header.is_init_segment:
            raise SabrStreamError(f'Sequence number not found in MediaHeader (media_header={media_header})')

        initialized_format.sequence_lmt = media_header.sequence_lmt

        # Need to keep track of if we discard due to be consumed or not
        # for processing down the line (MediaEnd)
        consumed = False
        discard = initialized_format.discard

        # Guard: Check if sequence number is within any existing consumed range
        # The server should not send us any segments that are already consumed
        # However, if retrying a request, we may get the same segment again
        if not is_init_segment and any(
            cr.start_sequence_number <= sequence_number <= cr.end_sequence_number
            for cr in initialized_format.consumed_ranges
        ):
            self.logger.debug(f'{initialized_format.format_id} segment {sequence_number} already consumed, marking segment as consumed')
            consumed = True

        # Validate that the segment is in order.
        # Note: If the format is to be discarded, we do not care about the order
        #  and can expect uncommanded seeks as the consumer does not know about it.
        # Note: previous segment should never be an init segment.
        previous_segment = initialized_format.current_segment
        if (
            previous_segment and not is_init_segment
            and not previous_segment.discard and not discard and not consumed
            and sequence_number != previous_segment.sequence_number + 1
        ):
            # Bail out as the segment is not in order when it is expected to be
            raise MediaSegmentMismatchError(
                expected_sequence_number=previous_segment.sequence_number + 1,
                received_sequence_number=sequence_number,
                format_id=media_header.format_id)

        if initialized_format.init_segment and is_init_segment:
            self.logger.debug(
                f'Init segment {sequence_number} already seen for format {initialized_format.format_id}, marking segment as consumed')
            consumed = True

        time_range = media_header.time_range
        start_ms = media_header.start_ms or (time_range and ticks_to_ms(time_range.start_ticks, time_range.timescale)) or 0

        # Calculate duration of this segment
        # For videos, either duration_ms or time_range should be present
        # For live streams, calculate segment duration based on live metadata target segment duration
        actual_duration_ms = (
            media_header.duration_ms
            or (time_range and ticks_to_ms(time_range.duration_ticks, time_range.timescale)))

        estimated_duration_ms = None
        if self.is_live:
            # Underestimate the duration of the segment slightly as
            # the real duration may be slightly shorter than the target duration.
            estimated_duration_ms = (self.live_segment_target_duration_sec * 1000) - self.live_segment_target_duration_tolerance_ms
        elif is_init_segment:
            estimated_duration_ms = 0

        duration_ms = actual_duration_ms or estimated_duration_ms

        estimated_content_length = None
        if self.is_live and media_header.content_length is None and media_header.bitrate_bps is not None:
            estimated_content_length = math.ceil(media_header.bitrate_bps * (estimated_duration_ms / 1000))

        # Guard: Bail out if we cannot determine the duration, which we need to progress.
        if duration_ms is None:
            raise SabrStreamError(f'Cannot determine duration of segment {sequence_number} (media_header={media_header})')

        segment = Segment(
            format_id=media_header.format_id,
            is_init_segment=is_init_segment,
            duration_ms=duration_ms,
            start_data_range=media_header.start_data_range,
            sequence_number=sequence_number,
            content_length=media_header.content_length or estimated_content_length,
            content_length_estimated=estimated_content_length is not None,
            start_ms=start_ms,
            initialized_format=initialized_format,
            duration_estimated=not actual_duration_ms,
            discard=discard or consumed,
            consumed=consumed,
            sequence_lmt=media_header.sequence_lmt,
        )

        self.partial_segments[media_header.header_id] = segment

        if not segment.discard:
            result.sabr_part = MediaSegmentInitSabrPart(
                format_selector=segment.initialized_format.format_selector,
                format_id=segment.format_id,
                player_time_ms=self.client_abr_state.player_time_ms,
                sequence_number=segment.sequence_number,
                total_segments=segment.initialized_format.total_segments,
                duration_ms=segment.duration_ms,
                start_bytes=segment.start_data_range,
                start_time_ms=segment.start_ms,
                is_init_segment=segment.is_init_segment,
                content_length=segment.content_length,
                content_length_estimated=segment.content_length_estimated,
            )

        self.logger.trace(
            f'Initialized Media Header {media_header.header_id} for sequence {sequence_number}. Segment: {segment}')

        return result

    def process_media(self, header_id: int, content_length: int, data: io.BufferedIOBase) -> ProcessMediaResult:
        result = ProcessMediaResult()
        segment = self.partial_segments.get(header_id)
        if not segment:
            self.logger.debug(f'Header ID {header_id} not found')
            return result

        segment_start_bytes = segment.received_data_length
        segment.received_data_length += content_length

        if not segment.discard:
            result.sabr_part = MediaSegmentDataSabrPart(
                format_selector=segment.initialized_format.format_selector,
                format_id=segment.format_id,
                sequence_number=segment.sequence_number,
                is_init_segment=segment.is_init_segment,
                total_segments=segment.initialized_format.total_segments,
                data=data.read(),
                content_length=content_length,
                segment_start_bytes=segment_start_bytes,
            )

        return result

    def process_media_end(self, header_id: int) -> ProcessMediaEndResult:
        result = ProcessMediaEndResult()
        segment = self.partial_segments.pop(header_id, None)
        if not segment:
            # Should only happen due to server issue,
            # or we have an uninitialized format (which itself should not happen)
            self.logger.warning(f'Received a MediaEnd for an unknown or already finished header ID {header_id}')
            return result

        self.logger.trace(
            f'MediaEnd for {segment.format_id} (sequence {segment.sequence_number}, data length = {segment.received_data_length})')

        if segment.content_length is not None and segment.received_data_length != segment.content_length:
            if segment.content_length_estimated:
                self.logger.trace(
                    f'Content length for {segment.format_id} (sequence {segment.sequence_number}) was estimated, '
                    f'estimated {segment.content_length} bytes, got {segment.received_data_length} bytes')
            else:
                raise SabrStreamError(
                    f'Content length mismatch for {segment.format_id} (sequence {segment.sequence_number}): '
                    f'expected {segment.content_length} bytes, got {segment.received_data_length} bytes',
                )

        # Only count received segments as new segments if they are not discarded (consumed)
        # or it was part of a format that was discarded (but not consumed).
        # The latter can happen if the format is to be discarded but was not marked as fully consumed.
        if not segment.discard or (segment.initialized_format.discard and not segment.consumed):
            result.is_new_segment = True

        # Return the segment here instead of during MEDIA part(s) because:
        # 1. We can validate that we received the correct data length
        # 2. In the case of a retry during segment media, the partial data is not sent to the consumer
        if not segment.discard:
            # This needs to be yielded AFTER we have processed the segment
            # So the consumer can see the updated consumed ranges and use them for e.g. syncing between concurrent streams
            result.sabr_part = MediaSegmentEndSabrPart(
                format_selector=segment.initialized_format.format_selector,
                format_id=segment.format_id,
                sequence_number=segment.sequence_number,
                is_init_segment=segment.is_init_segment,
                total_segments=segment.initialized_format.total_segments,
            )
        else:
            self.logger.trace(f'Discarding media for {segment.initialized_format.format_id}')

        if segment.is_init_segment:
            segment.initialized_format.init_segment = segment
            # Do not create a consumed range for init segments
            return result

        if segment.initialized_format.current_segment and self.is_live:
            previous_segment = segment.initialized_format.current_segment
            self.logger.trace(
                f'Previous segment {previous_segment.sequence_number} for format {segment.format_id} '
                f'estimated duration difference from this segment ({segment.sequence_number}): {segment.start_ms - (previous_segment.start_ms + previous_segment.duration_ms)}ms')

        segment.initialized_format.current_segment = segment

        # Try to find a consumed range for this segment in sequence
        consumed_range = next(
            (cr for cr in segment.initialized_format.consumed_ranges if cr.end_sequence_number == segment.sequence_number - 1),
            None,
        )

        if not consumed_range and any(
            cr.start_sequence_number <= segment.sequence_number <= cr.end_sequence_number
            for cr in segment.initialized_format.consumed_ranges
        ):
            # Segment is already consumed, do not create a new consumed range. It was probably discarded.
            # This can be expected to happen in the case of video-only, where we discard the audio track (and mark it as entirely buffered)
            # We still want to create/update consumed range for discarded media IF it is not already consumed
            self.logger.debug(f'{segment.format_id} segment {segment.sequence_number} already consumed, not creating or updating consumed range (discard={segment.discard})')
            return result

        if not consumed_range:
            # Create a new consumed range starting from this segment
            segment.initialized_format.consumed_ranges.append(ConsumedRange(
                start_time_ms=segment.start_ms,
                duration_ms=segment.duration_ms,
                start_sequence_number=segment.sequence_number,
                end_sequence_number=segment.sequence_number,
            ))
            self.logger.debug(f'Created new consumed range for {segment.initialized_format.format_id} {segment.initialized_format.consumed_ranges[-1]}')
            return result

        # Update the existing consumed range to include this segment
        consumed_range.end_sequence_number = segment.sequence_number
        consumed_range.duration_ms = (segment.start_ms - consumed_range.start_time_ms) + segment.duration_ms

        # TODO: Conduct a seek on consumed ranges

        return result

    def process_live_metadata(self, live_metadata: LiveMetadata) -> ProcessLiveMetadataResult:
        self.live_metadata = live_metadata
        if self.live_metadata.head_sequence_time_ms:
            self.total_duration_ms = self.live_metadata.head_sequence_time_ms

        # If we have a head sequence number, we need to update the total sequences for each initialized format
        # For livestreams, it is not available in the format initialization metadata
        if self.live_metadata.head_sequence_number:
            for izf in self.initialized_formats.values():
                izf.total_segments = self.live_metadata.head_sequence_number

        result = ProcessLiveMetadataResult()

        # If the current player time is less than the min dvr time, simulate a server seek to the min dvr time.
        # The server SHOULD send us a SABR_SEEK part in this case, but it does not always happen (e.g. ANDROID_VR)
        # The server SHOULD NOT send us segments before the min dvr time, so we should assume that the player time is correct.
        min_seekable_time_ms = ticks_to_ms(self.live_metadata.min_seekable_time_ticks, self.live_metadata.min_seekable_timescale)
        if min_seekable_time_ms is not None and self.client_abr_state.player_time_ms < min_seekable_time_ms:
            self.logger.debug(f'Player time {self.client_abr_state.player_time_ms} is less than min seekable time {min_seekable_time_ms}, simulating server seek')
            self.client_abr_state.player_time_ms = min_seekable_time_ms

            for izf in self.initialized_formats.values():
                izf.current_segment = None  # Clear the current segment as we expect segments to no longer be in order.
                result.seek_sabr_parts.append(MediaSeekSabrPart(
                    reason=MediaSeekSabrPart.Reason.SERVER_SEEK,
                    format_id=izf.format_id,
                    format_selector=izf.format_selector,
                ))

        return result

    def process_stream_protection_status(self, stream_protection_status: StreamProtectionStatus) -> ProcessStreamProtectionStatusResult:
        self.stream_protection_status = stream_protection_status.status
        status = stream_protection_status.status
        po_token = self.po_token

        if status == StreamProtectionStatus.Status.OK:
            result_status = (
                PoTokenStatusSabrPart.PoTokenStatus.OK if po_token
                else PoTokenStatusSabrPart.PoTokenStatus.NOT_REQUIRED
            )
        elif status == StreamProtectionStatus.Status.ATTESTATION_PENDING:
            result_status = (
                PoTokenStatusSabrPart.PoTokenStatus.PENDING if po_token
                else PoTokenStatusSabrPart.PoTokenStatus.PENDING_MISSING
            )
        elif status == StreamProtectionStatus.Status.ATTESTATION_REQUIRED:
            result_status = (
                PoTokenStatusSabrPart.PoTokenStatus.INVALID if po_token
                else PoTokenStatusSabrPart.PoTokenStatus.MISSING
            )
        else:
            self.logger.warning(f'Received an unknown StreamProtectionStatus: {stream_protection_status}')
            result_status = None

        sabr_part = PoTokenStatusSabrPart(status=result_status) if result_status is not None else None
        return ProcessStreamProtectionStatusResult(sabr_part)

    def process_format_initialization_metadata(self, format_init_metadata: FormatInitializationMetadata) -> ProcessFormatInitializationMetadataResult:
        result = ProcessFormatInitializationMetadataResult()
        if str(format_init_metadata.format_id) in self.initialized_formats:
            self.logger.trace(f'Format {format_init_metadata.format_id} already initialized')
            return result

        if format_init_metadata.video_id and self.video_id and format_init_metadata.video_id != self.video_id:
            raise SabrStreamError(
                f'Received unexpected Format Initialization Metadata for video'
                f' {format_init_metadata.video_id} (expecting {self.video_id})')

        format_selector = self.match_format_selector(format_init_metadata)
        if not format_selector:
            # Should not happen. If we ignored the format the server may refuse to send us any more data
            raise SabrStreamError(f'Received format {format_init_metadata.format_id} but it does not match any format selector')

        # Guard: Check if the format selector is already in use by another initialized format.
        # This can happen when the server changes the format to use (e.g. changing quality).
        #
        # Changing a format will require adding some logic to handle inactive formats.
        # Given we only provide one FormatId currently, and this should not occur in this case,
        # we will mark this as not currently supported and bail.
        for izf in self.initialized_formats.values():
            if izf.format_selector is format_selector:
                raise SabrStreamError('Server changed format. Changing formats is not currently supported')

        duration_ms = ticks_to_ms(format_init_metadata.duration_ticks, format_init_metadata.duration_timescale)

        total_segments = format_init_metadata.total_segments
        if not total_segments and self.live_metadata and self.live_metadata.head_sequence_number:
            total_segments = self.live_metadata.head_sequence_number

        initialized_format = InitializedFormat(
            format_id=format_init_metadata.format_id,
            duration_ms=duration_ms,
            end_time_ms=format_init_metadata.end_time_ms,
            mime_type=format_init_metadata.mime_type,
            video_id=format_init_metadata.video_id,
            format_selector=format_selector,
            total_segments=total_segments,
            discard=format_selector.discard_media,
        )
        self.total_duration_ms = max(self.total_duration_ms or 0, format_init_metadata.end_time_ms or 0, duration_ms or 0)

        if initialized_format.discard:
            # Mark the entire format as buffered into oblivion if we plan to discard all media.
            # This stops the server sending us any more data for this format.
            # Note: Using JS_MAX_SAFE_INTEGER but could use any maximum value as long as the server accepts it.
            initialized_format.consumed_ranges = [ConsumedRange(
                start_time_ms=0,
                duration_ms=(2**53) - 1,
                start_sequence_number=0,
                end_sequence_number=(2**53) - 1,
            )]

        self.initialized_formats[str(format_init_metadata.format_id)] = initialized_format
        self.logger.debug(f'Initialized Format: {initialized_format}')

        if not initialized_format.discard:
            result.sabr_part = FormatInitializedSabrPart(
                format_id=format_init_metadata.format_id,
                format_selector=format_selector,
            )

        return ProcessFormatInitializationMetadataResult(sabr_part=result.sabr_part)

    def process_next_request_policy(self, next_request_policy: NextRequestPolicy):
        self.next_request_policy = next_request_policy
        self.logger.trace(f'Registered new NextRequestPolicy: {self.next_request_policy}')

    def process_sabr_seek(self, sabr_seek: SabrSeek) -> ProcessSabrSeekResult:
        seek_to = ticks_to_ms(sabr_seek.seek_time_ticks, sabr_seek.timescale)
        if seek_to is None:
            raise SabrStreamError(f'Server sent a SabrSeek part that is missing required seek data: {sabr_seek}')
        self.logger.debug(f'Seeking to {seek_to}ms')
        self.client_abr_state.player_time_ms = seek_to

        result = ProcessSabrSeekResult()

        # Clear latest segment of each initialized format
        #  as we expect them to no longer be in order.
        for initialized_format in self.initialized_formats.values():
            initialized_format.current_segment = None
            result.seek_sabr_parts.append(MediaSeekSabrPart(
                reason=MediaSeekSabrPart.Reason.SERVER_SEEK,
                format_id=initialized_format.format_id,
                format_selector=initialized_format.format_selector,
            ))
        return result

    def process_sabr_context_update(self, sabr_ctx_update: SabrContextUpdate):
        if not (sabr_ctx_update.type and sabr_ctx_update.value and sabr_ctx_update.write_policy):
            self.logger.warning('Received an invalid SabrContextUpdate, ignoring')
            return

        if (
            sabr_ctx_update.write_policy == SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_KEEP_EXISTING
            and sabr_ctx_update.type in self.sabr_context_updates
        ):
            self.logger.debug(
                'Received a SABR Context Update with write_policy=KEEP_EXISTING'
                'matching an existing SABR Context Update. Ignoring update')
            return

        self.logger.warning(
            'Received a SABR Context Update. YouTube is likely trying to force ads on the client. '
            'This may cause issues with playback.')

        self.sabr_context_updates[sabr_ctx_update.type] = sabr_ctx_update
        if sabr_ctx_update.send_by_default is True:
            self.sabr_contexts_to_send.add(sabr_ctx_update.type)
        self.logger.debug(f'Registered SabrContextUpdate {sabr_ctx_update}')

    def process_sabr_context_sending_policy(self, sabr_ctx_sending_policy: SabrContextSendingPolicy):
        for start_type in sabr_ctx_sending_policy.start_policy:
            if start_type not in self.sabr_contexts_to_send:
                self.logger.debug(f'Server requested to enable SABR Context Update for type {start_type}')
                self.sabr_contexts_to_send.add(start_type)

        for stop_type in sabr_ctx_sending_policy.stop_policy:
            if stop_type in self.sabr_contexts_to_send:
                self.logger.debug(f'Server requested to disable SABR Context Update for type {stop_type}')
                self.sabr_contexts_to_send.remove(stop_type)

        for discard_type in sabr_ctx_sending_policy.discard_policy:
            if discard_type in self.sabr_context_updates:
                self.logger.debug(f'Server requested to discard SABR Context Update for type {discard_type}')
                self.sabr_context_updates.pop(discard_type, None)


def build_vpabr_request(processor: SabrProcessor):
    return VideoPlaybackAbrRequest(
        client_abr_state=processor.client_abr_state,
        selected_video_format_ids=processor.selected_video_format_ids,
        selected_audio_format_ids=processor.selected_audio_format_ids,
        selected_caption_format_ids=processor.selected_caption_format_ids,
        initialized_format_ids=[
            initialized_format.format_id for initialized_format in processor.initialized_formats.values()
        ],
        video_playback_ustreamer_config=base64.urlsafe_b64decode(processor.video_playback_ustreamer_config),
        streamer_context=StreamerContext(
            po_token=base64.urlsafe_b64decode(processor.po_token) if processor.po_token is not None else None,
            playback_cookie=processor.next_request_policy.playback_cookie if processor.next_request_policy is not None else None,
            client_info=processor.client_info,
            sabr_contexts=[
                SabrContext(context.type, context.value)
                for context in processor.sabr_context_updates.values()
                if context.type in processor.sabr_contexts_to_send
            ],
            unsent_sabr_contexts=[
                context_type for context_type in processor.sabr_contexts_to_send
                if context_type not in processor.sabr_context_updates
            ],
        ),
        buffered_ranges=[
            BufferedRange(
                format_id=initialized_format.format_id,
                start_segment_index=cr.start_sequence_number,
                end_segment_index=cr.end_sequence_number,
                start_time_ms=cr.start_time_ms,
                duration_ms=cr.duration_ms,
                time_range=TimeRange(
                    start_ticks=cr.start_time_ms,
                    duration_ticks=cr.duration_ms,
                    timescale=1000,
                ),
            ) for initialized_format in processor.initialized_formats.values()
            for cr in initialized_format.consumed_ranges
        ],
    )
