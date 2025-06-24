from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import math
import time
import typing
import urllib.parse

from yt_dlp.dependencies import protobug
from yt_dlp.extractor.youtube._proto import unknown_fields
from yt_dlp.extractor.youtube._proto.innertube import ClientInfo, NextRequestPolicy
from yt_dlp.extractor.youtube._proto.videostreaming import (
    FormatInitializationMetadata,
    LiveMetadata,
    MediaHeader,
    ReloadPlayerResponse,
    SabrContextSendingPolicy,
    SabrContextUpdate,
    SabrError,
    SabrRedirect,
    SabrSeek,
    StreamProtectionStatus,
)
from yt_dlp.networking import Request, Response
from yt_dlp.networking.exceptions import HTTPError, TransportError
from yt_dlp.utils import RetryManager, int_or_none, parse_qs, str_or_none, traverse_obj

from .exceptions import MediaSegmentMismatchError, PoTokenError, SabrStreamConsumedError, SabrStreamError
from .models import AudioSelector, CaptionSelector, SabrLogger, VideoSelector
from .part import (
    MediaSeekSabrPart,
    RefreshPlayerResponseSabrPart,
)
from .processor import SabrProcessor, build_vpabr_request
from .utils import broadcast_id_from_url, get_cr_chain, next_gvs_fallback_url
from ..ump import UMPDecoder, UMPPart, UMPPartId, read_varint


class SabrStream:

    """

    A YouTube SABR (Server Adaptive Bit Rate) client implementation designed for downloading streams and videos.

    It presents an iterator (iter_parts) that yields the next available segments and other metadata.

    Parameters:
    @param urlopen: A callable that takes a Request and returns a Response. Raises TransportError or HTTPError on failure.
    @param logger: The logger.
    @param server_abr_streaming_url: SABR streaming URL.
    @param video_playback_ustreamer_config: The base64url encoded ustreamer config.
    @param client_info: The Innertube client info.
    @param audio_selection: The audio format selector to use for audio.
    @param video_selection: The video format selector to use for video.
    @param caption_selection: The caption format selector to use for captions.
    @param live_segment_target_duration_sec: The target duration of live segments in seconds.
    @param live_segment_target_duration_tolerance_ms: The tolerance to accept for estimated duration of live segment in milliseconds.
    @param start_time_ms: The time in milliseconds to start playback from.
    @param po_token: Initial GVS PO Token.
    @param http_retries: The maximum number of times to retry a request before failing.
    @param pot_retries: The maximum number of times to retry PO Token errors before failing.
    @param host_fallback_threshold: The number of consecutive retries before falling back to the next GVS server.
    @param max_empty_requests: The maximum number of consecutive requests with no new segments before giving up.
    @param live_end_wait_sec: The number of seconds to wait after the last received segment before considering the live stream ended.
    @param live_end_segment_tolerance: The number of segments before the live head segment at which the livestream is allowed to end. Defaults to 10.
    @param post_live: Whether the live stream is in post-live mode. Used to determine how to handle the end of the stream.
    @param video_id: The video ID of the YouTube video. Used for validating received data is for the correct video.
    @param retry_sleep_func: A function to sleep between retries. If None, will not sleep between retries.
    @param expiry_threshold_sec: The number of seconds before the GVS expiry to consider it expired. Defaults to 1 minute.
    """

    # Used for debugging
    _IGNORED_PARTS = (
        UMPPartId.REQUEST_IDENTIFIER,
        UMPPartId.REQUEST_CANCELLATION_POLICY,
        UMPPartId.PLAYBACK_START_POLICY,
        UMPPartId.ALLOWED_CACHED_FORMATS,
        UMPPartId.PAUSE_BW_SAMPLING_HINT,
        UMPPartId.START_BW_SAMPLING_HINT,
        UMPPartId.REQUEST_PIPELINING,
        UMPPartId.SELECTABLE_FORMATS,
        UMPPartId.PREWARM_CONNECTION,
    )

    @dataclasses.dataclass
    class _NoSegmentsTracker:
        consecutive_requests: int = 0
        timestamp_started: float | None = None
        live_head_segment_started: int | None = None

        def reset(self):
            self.consecutive_requests = 0
            self.timestamp_started = None
            self.live_head_segment_started = None

        def increment(self, live_head_segment=None):
            if self.consecutive_requests == 0:
                self.timestamp_started = time.time()
                self.live_head_segment_started = live_head_segment
            self.consecutive_requests += 1

    def __init__(
        self,
        urlopen: typing.Callable[[Request], Response],
        logger: SabrLogger,
        server_abr_streaming_url: str,
        video_playback_ustreamer_config: str,
        client_info: ClientInfo,
        audio_selection: AudioSelector | None = None,
        video_selection: VideoSelector | None = None,
        caption_selection: CaptionSelector | None = None,
        live_segment_target_duration_sec: int | None = None,
        live_segment_target_duration_tolerance_ms: int | None = None,
        start_time_ms: int | None = None,
        po_token: str | None = None,
        http_retries: int | None = None,
        pot_retries: int | None = None,
        host_fallback_threshold: int | None = None,
        max_empty_requests: int | None = None,
        live_end_wait_sec: int | None = None,
        live_end_segment_tolerance: int | None = None,
        post_live: bool = False,
        video_id: str | None = None,
        retry_sleep_func: int | None = None,
        expiry_threshold_sec: int | None = None,
    ):

        self.logger = logger
        self._urlopen = urlopen

        self.processor = SabrProcessor(
            logger=logger,
            video_playback_ustreamer_config=video_playback_ustreamer_config,
            client_info=client_info,
            audio_selection=audio_selection,
            video_selection=video_selection,
            caption_selection=caption_selection,
            live_segment_target_duration_sec=live_segment_target_duration_sec,
            live_segment_target_duration_tolerance_ms=live_segment_target_duration_tolerance_ms,
            start_time_ms=start_time_ms,
            po_token=po_token,
            post_live=post_live,
            video_id=video_id,
        )
        self.url = server_abr_streaming_url
        self.http_retries = http_retries or 10
        self.pot_retries = pot_retries or 5
        self.host_fallback_threshold = host_fallback_threshold or 8
        self.max_empty_requests = max_empty_requests or 3
        self.live_end_wait_sec = live_end_wait_sec or max(10, self.max_empty_requests * self.processor.live_segment_target_duration_sec)
        self.live_end_segment_tolerance = live_end_segment_tolerance or 10
        self.expiry_threshold_sec = expiry_threshold_sec or 60  # 60 seconds
        if self.expiry_threshold_sec <= 0:
            raise ValueError('expiry_threshold_sec must be greater than 0')
        if self.max_empty_requests <= 0:
            raise ValueError('max_empty_requests must be greater than 0')
        self.retry_sleep_func = retry_sleep_func
        self._request_number = 0

        # Whether we got any new (not consumed) segments in the request.
        self._received_new_segments = False
        self._no_new_segments_tracker = SabrStream._NoSegmentsTracker()
        self._sps_retry_manager: typing.Generator | None = None
        self._current_sps_retry = None
        self._http_retry_manager: typing.Generator | None = None
        self._current_http_retry = None
        self._unknown_part_types = set()

        # Whether the current request is a result of a retry
        self._is_retry = False

        self._consumed = False
        self._sq_mismatch_backtrack_count = 0
        self._sq_mismatch_forward_count = 0

    def close(self):
        self._consumed = True

    def __iter__(self):
        return self.iter_parts()

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self.logger.debug(f'New URL: {url}')
        if hasattr(self, '_url') and ((bn := broadcast_id_from_url(url)) != (bc := broadcast_id_from_url(self.url))):
            raise SabrStreamError(f'Broadcast ID changed from {bc} to {bn}. The download will need to be restarted.')
        self._url = url
        if str_or_none(parse_qs(url).get('source', [None])[0]) == 'yt_live_broadcast':
            self.processor.is_live = True

    def iter_parts(self):
        if self._consumed:
            raise SabrStreamConsumedError('SABR stream has already been consumed')

        self._http_retry_manager = None
        self._sps_retry_manager = None

        def report_retry(err, count, retries, fatal=True):
            if count >= self.host_fallback_threshold:
                self._process_fallback_server()
            RetryManager.report_retry(
                err, count, retries, info=self.logger.info,
                warn=lambda msg: self.logger.warning(f'[sabr] Got error: {msg}'),
                error=None if fatal else lambda msg: self.logger.warning(f'[sabr] Got error: {msg}'),
                sleep_func=self.retry_sleep_func,
            )

        def report_sps_retry(err, count, retries, fatal=True):
            RetryManager.report_retry(
                err, count, retries, info=self.logger.info,
                warn=lambda msg: self.logger.warning(f'[sabr] Got error: {msg}'),
                error=None if fatal else lambda msg: self.logger.warning(f'[sabr] Got error: {msg}'),
                sleep_func=self.retry_sleep_func,
            )

        while not self._consumed:
            if self._http_retry_manager is None:
                self._http_retry_manager = iter(RetryManager(self.http_retries, report_retry))

            if self._sps_retry_manager is None:
                self._sps_retry_manager = iter(RetryManager(self.pot_retries, report_sps_retry))

            self._current_http_retry = next(self._http_retry_manager)
            self._current_sps_retry = next(self._sps_retry_manager)

            self._log_state()

            yield from self._process_expiry()
            vpabr = build_vpabr_request(self.processor)
            payload = protobug.dumps(vpabr)
            self.logger.trace(f'Ustreamer Config: {self.processor.video_playback_ustreamer_config}')
            self.logger.trace(f'Sending SABR request: {vpabr}')

            response = None
            try:
                response = self._urlopen(
                    Request(
                        url=self.url,
                        method='POST',
                        data=payload,
                        query={'rn': self._request_number},
                        headers={
                            'content-type': 'application/x-protobuf',
                            'accept-encoding': 'identity',
                            'accept': 'application/vnd.yt-ump',
                        },
                    ),
                )
                self._request_number += 1
            except TransportError as e:
                self._current_http_retry.error = e
            except HTTPError as e:
                # retry on 5xx errors only
                if 500 <= e.status < 600:
                    self._current_http_retry.error = e
                else:
                    raise SabrStreamError(f'HTTP Error: {e.status} - {e.reason}')

            if response:
                try:
                    yield from self._parse_ump_response(response)
                except TransportError as e:
                    self._current_http_retry.error = e

                if not response.closed:
                    response.close()

            self._validate_response_integrity()
            self._process_sps_retry()

            if not self._current_http_retry.error:
                self._http_retry_manager = None

            if not self._current_sps_retry.error:
                self._sps_retry_manager = None

            retry_next_request = bool(self._current_http_retry.error or self._current_sps_retry.error)

            # We are expecting to stay in the same place for a retry
            if not retry_next_request:
                # Only increment request no segments number if we are not retrying
                self._process_request_had_segments()

                # Calculate and apply the next playback time to skip to
                yield from self._prepare_next_playback_time()

                # Request successfully processed, next request is not a retry
                self._is_retry = False
            else:
                self._is_retry = True

            self._received_new_segments = False

        self._consumed = True

    def _process_sps_retry(self):
        error = PoTokenError(missing=not self.processor.po_token)

        if self.processor.stream_protection_status == StreamProtectionStatus.Status.ATTESTATION_REQUIRED:
            # Always start retrying immediately on ATTESTATION_REQUIRED
            self._current_sps_retry.error = error
            return

        elif (
            self.processor.stream_protection_status == StreamProtectionStatus.Status.ATTESTATION_PENDING
            and self._no_new_segments_tracker.consecutive_requests >= self.max_empty_requests
            and (not self.processor.is_live or self.processor.stream_protection_status or (
                self.processor.live_metadata is not None
                and self._no_new_segments_tracker.live_head_segment_started != self.processor.live_metadata.head_sequence_number)
            )
        ):
            # Sometimes YouTube sends no data on ATTESTATION_PENDING, so in this case we need to count retries to fail on a PO Token error.
            # We only start counting retries after max_empty_requests in case of intermittent no data that we need to increase the player time on.
            # For livestreams when we receive no new segments, this could be due the stream ending or ATTESTATION_PENDING.
            # To differentiate the two, we check if the live head segment has changed during the time we start getting no new segments.
            # xxx: not perfect detection, sometimes get a new segment we can never fetch (partial)
            self._current_sps_retry.error = error
            return

    def _process_request_had_segments(self):
        if not self._received_new_segments:
            self._no_new_segments_tracker.increment(
                live_head_segment=self.processor.live_metadata.head_sequence_number if self.processor.live_metadata else None)
            self.logger.trace(f'No new segments received in request {self._request_number}, count: {self._no_new_segments_tracker.consecutive_requests}')
        else:
            self._no_new_segments_tracker.reset()

    def _validate_response_integrity(self):
        if not len(self.processor.partial_segments):
            return

        msg = 'Received partial segments: ' + ', '.join(
            f'{seg.format_id}: {seg.sequence_number}'
            for seg in self.processor.partial_segments.values()
        )
        if self.processor.is_live:
            # In post live, sometimes we get a partial segment at the end of the stream that should be ignored.
            # If this occurs mid-stream, other guards should prevent corruption.
            if (
                self.processor.live_metadata
                # TODO: generalize
                and self.processor.client_abr_state.player_time_ms >= (
                    self.processor.live_metadata.head_sequence_time_ms - (self.processor.live_segment_target_duration_sec * 1000 * self.live_end_segment_tolerance))
            ):
                # Only log a warning if we are not near the head of a stream
                self.logger.debug(msg)
            else:
                self.logger.warning(msg)
        else:
            # Should not happen for videos
            self._current_http_retry.error = SabrStreamError(msg)

        self.processor.partial_segments.clear()

    def _prepare_next_playback_time(self):
        # TODO: refactor and cleanup this massive function
        wait_seconds = 0
        for izf in self.processor.initialized_formats.values():
            if not izf.current_segment:
                continue

            # Guard: Check that the segment is not in multiple consumed ranges
            # This should not happen, but if it does, we should bail
            count = sum(
                1 for cr in izf.consumed_ranges
                if cr.start_sequence_number <= izf.current_segment.sequence_number <= cr.end_sequence_number
            )

            if count > 1:
                raise SabrStreamError(f'Segment {izf.current_segment.sequence_number} for format {izf.format_id} in {count} consumed ranges')

            # Check if there is two or more consumed ranges where the end lines up with the start of the other.
            # This could happen in the case of concurrent playback.
            # In this case, we should consider a seek as acceptable to the end of the other.
            # Note: It is assumed a segment is only present in one consumed range - it should not be allowed in multiple (by process media header)
            prev_consumed_range = next(
                (cr for cr in izf.consumed_ranges if cr.end_sequence_number == izf.current_segment.sequence_number),
                None,
            )
            # TODO: move to processor MEDIA_END
            if prev_consumed_range and len(get_cr_chain(prev_consumed_range, izf.consumed_ranges)) >= 2:
                self.logger.debug(f'Found two or more consumed ranges that line up, allowing a seek for format {izf.format_id}')
                izf.current_segment = None
                yield MediaSeekSabrPart(
                    reason=MediaSeekSabrPart.Reason.CONSUMED_SEEK,
                    format_id=izf.format_id,
                    format_selector=izf.format_selector)

        enabled_initialized_formats = [izf for izf in self.processor.initialized_formats.values() if not izf.discard]

        # For each initialized format:
        #   1. find the consumed format that matches player_time_ms.
        #   2. find the current consumed range in sequence (in case multiple are joined together)
        # For livestreams, we allow a tolerance for the segment duration as it is estimated. This tolerance should be less than the segment duration / 2.

        cr_tolerance_ms = 0
        if self.processor.is_live:
            cr_tolerance_ms = self.processor.live_segment_target_duration_tolerance_ms

        current_consumed_ranges = []
        for izf in enabled_initialized_formats:
            for cr in sorted(izf.consumed_ranges, key=lambda cr: cr.start_sequence_number):
                if (cr.start_time_ms - cr_tolerance_ms) <= self.processor.client_abr_state.player_time_ms <= cr.start_time_ms + cr.duration_ms + (cr_tolerance_ms * 2):
                    chain = get_cr_chain(cr, izf.consumed_ranges)
                    current_consumed_ranges.append(chain[-1])
                    # There should only be one chain for the current player_time_ms (including the tolerance)
                    break

        min_consumed_duration_ms = None

        # Get the lowest consumed range end time out of all current consumed ranges.
        if current_consumed_ranges:
            lowest_izf_consumed_range = min(current_consumed_ranges, key=lambda cr: cr.start_time_ms + cr.duration_ms)
            min_consumed_duration_ms = lowest_izf_consumed_range.start_time_ms + lowest_izf_consumed_range.duration_ms

        if len(current_consumed_ranges) != len(enabled_initialized_formats) or min_consumed_duration_ms is None:
            # Missing a consumed range for a format.
            # In this case, consider player_time_ms to be our correct next time
            # May happen in the case of:
            # 1. A Format has not been initialized yet (can happen if response read fails)
            # or
            # 1. SABR_SEEK to time outside both formats consumed ranges
            # 2. ONE of the formats returns data after the SABR_SEEK in that request
            if min_consumed_duration_ms is None:
                min_consumed_duration_ms = self.processor.client_abr_state.player_time_ms
            else:
                min_consumed_duration_ms = min(min_consumed_duration_ms, self.processor.client_abr_state.player_time_ms)

        # Usually provided by the server if there was no segments returned.
        # We'll use this to calculate the time to wait for the next request (for live streams).
        next_request_backoff_ms = (self.processor.next_request_policy and self.processor.next_request_policy.backoff_time_ms) or 0

        request_player_time = self.processor.client_abr_state.player_time_ms
        self.logger.trace(f'min consumed duration ms: {min_consumed_duration_ms}')
        self.processor.client_abr_state.player_time_ms = min_consumed_duration_ms

        # Check if the latest segment is the last one of each format (if data is available)
        if (
            not (self.processor.is_live and not self.processor.post_live)
            and enabled_initialized_formats
            and len(current_consumed_ranges) == len(enabled_initialized_formats)
            and all(
                (
                    initialized_format.total_segments is not None
                    # consumed ranges are not guaranteed to be in order
                    and sorted(
                        initialized_format.consumed_ranges,
                        key=lambda cr: cr.end_sequence_number,
                    )[-1].end_sequence_number >= initialized_format.total_segments
                )
                for initialized_format in enabled_initialized_formats
            )
        ):
            self.logger.debug('Reached last expected segment for all enabled formats, assuming end of media')
            self._consumed = True

        # Check if we have exceeded the total duration of the media (if not live),
        #  or wait for the next segment (if live)
        elif self.processor.total_duration_ms and (self.processor.client_abr_state.player_time_ms >= self.processor.total_duration_ms):
            if self.processor.is_live:
                self.logger.trace(f'setting player time ms ({self.processor.client_abr_state.player_time_ms}) to total duration ms ({self.processor.total_duration_ms})')
                self.processor.client_abr_state.player_time_ms = self.processor.total_duration_ms
                if (
                    self._no_new_segments_tracker.consecutive_requests > self.max_empty_requests
                    and not self._is_retry
                    and self._no_new_segments_tracker.timestamp_started < time.time() + self.live_end_wait_sec
                ):
                    self.logger.debug(f'No new segments received for at least {self.live_end_wait_sec} seconds, assuming end of live stream')
                    self._consumed = True
                else:
                    wait_seconds = max(next_request_backoff_ms / 1000, self.processor.live_segment_target_duration_sec)
            else:
                self.logger.debug(f'End of media (player time ms {self.processor.client_abr_state.player_time_ms} >= total duration ms {self.processor.total_duration_ms})')
                self._consumed = True

        # Handle receiving no new segments before end the end of the video/stream
        # For videos, if exceeds max_empty_requests, this should not happen so we raise an error
        # For livestreams, if we exceed max_empty_requests, and we don't have live_metadata,
        #   and have not received any data for a while, we can assume the stream has ended (as we don't know the head sequence number)
        elif (
            # Determine if we are receiving no segments as the live stream has ended.
            # Allow some tolerance the head segment may not be able to be received.
            self.processor.is_live and not self.processor.post_live
            and (
                getattr(self.processor.live_metadata, 'head_sequence_number', None) is None
                or (
                    enabled_initialized_formats
                    and len(current_consumed_ranges) == len(enabled_initialized_formats)
                    and all(
                        (
                            initialized_format.total_segments is not None
                            and sorted(
                                initialized_format.consumed_ranges,
                                key=lambda cr: cr.end_sequence_number,
                            )[-1].end_sequence_number
                            >= initialized_format.total_segments - self.live_end_segment_tolerance
                        )
                        for initialized_format in enabled_initialized_formats
                    )
                )
                or self.processor.live_metadata.head_sequence_time_ms is None
                or (
                    # Sometimes we receive a partial segment at the end of the stream
                    # and the server seeks us to the end of the current segment.
                    # As our consumed range for this segment has an estimated end time,
                    # this may be slightly off what the server seeks to.
                    # This can cause the player time to be slightly outside the consumed range.
                    #
                    # Because of this, we should also check the player time against
                    # the head segment time using the estimated segment duration.
                    # xxx: consider also taking into account the max seekable timestamp
                    request_player_time >= self.processor.live_metadata.head_sequence_time_ms - (self.processor.live_segment_target_duration_sec * 1000 * self.live_end_segment_tolerance)
                )
            )
        ):
            if (
                not self._is_retry  # allow us to sleep on a retry
                and self._no_new_segments_tracker.consecutive_requests > self.max_empty_requests
                and self._no_new_segments_tracker.timestamp_started < time.time() + self.live_end_wait_sec
            ):
                self.logger.debug(f'No new segments received for at least {self.live_end_wait_sec} seconds; assuming end of live stream')
                self._consumed = True
            elif self._no_new_segments_tracker.consecutive_requests >= 1:
                # Sometimes we can't get the head segment - rather tend to sit behind the head segment for the duration of the livestream
                wait_seconds = max(next_request_backoff_ms / 1000, self.processor.live_segment_target_duration_sec)
        elif (
            self._no_new_segments_tracker.consecutive_requests > self.max_empty_requests
            and not self._is_retry
        ):
            raise SabrStreamError('No new segments received in three consecutive requests')

        elif (
            not self.processor.is_live and next_request_backoff_ms
            and self._no_new_segments_tracker.consecutive_requests >= 1
            and any(t in self.processor.sabr_contexts_to_send for t in self.processor.sabr_context_updates)
        ):
            wait_seconds = math.ceil(next_request_backoff_ms / 1000)
            self.logger.info(f'The server is requiring yt-dlp to wait {wait_seconds} seconds before continuing due to ad enforcement')

        if wait_seconds:
            self.logger.debug(f'Waiting {wait_seconds} seconds for next segment(s)')
            time.sleep(wait_seconds)

    def _parse_ump_response(self, response):
        self._unknown_part_types.clear()
        ump = UMPDecoder(response)
        for part in ump.iter_parts():
            if part.part_id == UMPPartId.MEDIA_HEADER:
                yield from self._process_media_header(part)
            elif part.part_id == UMPPartId.MEDIA:
                yield from self._process_media(part)
            elif part.part_id == UMPPartId.MEDIA_END:
                yield from self._process_media_end(part)
            elif part.part_id == UMPPartId.STREAM_PROTECTION_STATUS:
                yield from self._process_stream_protection_status(part)
            elif part.part_id == UMPPartId.SABR_REDIRECT:
                self._process_sabr_redirect(part)
            elif part.part_id == UMPPartId.FORMAT_INITIALIZATION_METADATA:
                yield from self._process_format_initialization_metadata(part)
            elif part.part_id == UMPPartId.NEXT_REQUEST_POLICY:
                self._process_next_request_policy(part)
            elif part.part_id == UMPPartId.LIVE_METADATA:
                yield from self._process_live_metadata(part)
            elif part.part_id == UMPPartId.SABR_SEEK:
                yield from self._process_sabr_seek(part)
            elif part.part_id == UMPPartId.SABR_ERROR:
                self._process_sabr_error(part)
            elif part.part_id == UMPPartId.SABR_CONTEXT_UPDATE:
                self._process_sabr_context_update(part)
            elif part.part_id == UMPPartId.SABR_CONTEXT_SENDING_POLICY:
                self._process_sabr_context_sending_policy(part)
            elif part.part_id == UMPPartId.RELOAD_PLAYER_RESPONSE:
                yield from self._process_reload_player_response(part)
            else:
                if part.part_id not in self._IGNORED_PARTS:
                    self._unknown_part_types.add(part.part_id)
                self._log_part(part, msg='Unhandled part type', data=part.data.read())

            # Cancel request processing if we are going to retry
            if self._current_sps_retry.error or self._current_http_retry.error:
                self.logger.debug('Request processing cancelled')
                return

    def _process_media_header(self, part: UMPPart):
        media_header = protobug.load(part.data, MediaHeader)
        self._log_part(part=part, protobug_obj=media_header)

        try:
            result = self.processor.process_media_header(media_header)
            if result.sabr_part:
                yield result.sabr_part
        except MediaSegmentMismatchError as e:
            # For livestreams, the server may not know the exact segment for a given player time.
            # For segments near stream head, it estimates using segment duration, which can cause off-by-one segment mismatches.
            # If a segment is much longer or shorter than expected, the server may return a segment ahead or behind.
            # In such cases, retry with an adjusted player time to resync.
            if self.processor.is_live and e.received_sequence_number == e.expected_sequence_number - 1:
                # The segment before the previous segment was possibly longer than expected.
                # Move the player time forward to try to adjust for this.
                self.processor.client_abr_state.player_time_ms += self.processor.live_segment_target_duration_tolerance_ms
                self._sq_mismatch_forward_count += 1
                self._current_http_retry.error = e
                return
            elif self.processor.is_live and e.received_sequence_number == e.expected_sequence_number + 2:
                # The previous segment was possibly shorter than expected
                # Move the player time backwards to try to adjust for this.
                self.processor.client_abr_state.player_time_ms = max(0, self.processor.client_abr_state.player_time_ms - self.processor.live_segment_target_duration_tolerance_ms)
                self._sq_mismatch_backtrack_count += 1
                self._current_http_retry.error = e
                return
            raise e

    def _process_media(self, part: UMPPart):
        header_id = read_varint(part.data)
        content_length = part.size - part.data.tell()
        result = self.processor.process_media(header_id, content_length, part.data)
        if result.sabr_part:
            yield result.sabr_part

    def _process_media_end(self, part: UMPPart):
        header_id = read_varint(part.data)
        self._log_part(part, msg=f'Header ID: {header_id}')

        result = self.processor.process_media_end(header_id)
        if result.is_new_segment:
            self._received_new_segments = True

        if result.sabr_part:
            yield result.sabr_part

    def _process_live_metadata(self, part: UMPPart):
        live_metadata = protobug.load(part.data, LiveMetadata)
        self._log_part(part, protobug_obj=live_metadata)
        yield from self.processor.process_live_metadata(live_metadata).seek_sabr_parts

    def _process_stream_protection_status(self, part: UMPPart):
        sps = protobug.load(part.data, StreamProtectionStatus)
        self._log_part(part, msg=f'Status: {StreamProtectionStatus.Status(sps.status).name}', protobug_obj=sps)
        result = self.processor.process_stream_protection_status(sps)
        if result.sabr_part:
            yield result.sabr_part

    def _process_sabr_redirect(self, part: UMPPart):
        sabr_redirect = protobug.load(part.data, SabrRedirect)
        self._log_part(part, protobug_obj=sabr_redirect)
        if not sabr_redirect.redirect_url:
            self.logger.warning('Server requested to redirect to an invalid URL')
            return
        self.url = sabr_redirect.redirect_url

    def _process_format_initialization_metadata(self, part: UMPPart):
        fmt_init_metadata = protobug.load(part.data, FormatInitializationMetadata)
        self._log_part(part, protobug_obj=fmt_init_metadata)
        result = self.processor.process_format_initialization_metadata(fmt_init_metadata)
        if result.sabr_part:
            yield result.sabr_part

    def _process_next_request_policy(self, part: UMPPart):
        next_request_policy = protobug.load(part.data, NextRequestPolicy)
        self._log_part(part, protobug_obj=next_request_policy)
        self.processor.process_next_request_policy(next_request_policy)

    def _process_sabr_seek(self, part: UMPPart):
        sabr_seek = protobug.load(part.data, SabrSeek)
        self._log_part(part, protobug_obj=sabr_seek)
        yield from self.processor.process_sabr_seek(sabr_seek).seek_sabr_parts

    def _process_sabr_error(self, part: UMPPart):
        sabr_error = protobug.load(part.data, SabrError)
        self._log_part(part, protobug_obj=sabr_error)
        self._current_http_retry.error = SabrStreamError(f'SABR Protocol Error: {sabr_error}')

    def _process_sabr_context_update(self, part: UMPPart):
        sabr_ctx_update = protobug.load(part.data, SabrContextUpdate)
        self._log_part(part, protobug_obj=sabr_ctx_update)
        self.processor.process_sabr_context_update(sabr_ctx_update)

    def _process_sabr_context_sending_policy(self, part: UMPPart):
        sabr_ctx_sending_policy = protobug.load(part.data, SabrContextSendingPolicy)
        self._log_part(part, protobug_obj=sabr_ctx_sending_policy)
        self.processor.process_sabr_context_sending_policy(sabr_ctx_sending_policy)

    def _process_reload_player_response(self, part: UMPPart):
        reload_player_response = protobug.load(part.data, ReloadPlayerResponse)
        self._log_part(part, protobug_obj=reload_player_response)
        yield RefreshPlayerResponseSabrPart(
            reason=RefreshPlayerResponseSabrPart.Reason.SABR_RELOAD_PLAYER_RESPONSE,
            reload_playback_token=reload_player_response.reload_playback_params.token,
        )

    def _process_fallback_server(self):
        # Attempt to fall back to another GVS host in the case the current one fails
        new_url = next_gvs_fallback_url(self.url)
        if not new_url:
            self.logger.debug('No more fallback hosts available')

        self.logger.warning(f'Falling back to host {urllib.parse.urlparse(new_url).netloc}')
        self.url = new_url

    def _gvs_expiry(self):
        return int_or_none(traverse_obj(parse_qs(self.url), ('expire', 0), get_all=False))

    def _process_expiry(self):
        expires_at = self._gvs_expiry()

        if not expires_at:
            self.logger.warning(
                'No expiry timestamp found in SABR URL. Will not be able to refresh.', once=True)
            return

        if expires_at - self.expiry_threshold_sec >= time.time():
            self.logger.trace(f'SABR url expires in {int(expires_at - time.time())} seconds')
            return

        self.logger.debug(
            f'Requesting player response refresh as SABR URL is due to expire in {self.expiry_threshold_sec} seconds')
        yield RefreshPlayerResponseSabrPart(reason=RefreshPlayerResponseSabrPart.Reason.SABR_URL_EXPIRY)

    def _log_part(self, part: UMPPart, msg=None, protobug_obj=None, data=None):
        if self.logger.log_level > self.logger.LogLevel.TRACE:
            return
        message = f'[{part.part_id.name}]: (Size {part.size})'
        if protobug_obj:
            message += f' Parsed: {protobug_obj}'
            uf = list(unknown_fields(protobug_obj))
            if uf:
                message += f' (Unknown fields: {uf})'
        if msg:
            message += f' {msg}'
        if data:
            message += f' Data: {base64.b64encode(data).decode("utf-8")}'
        self.logger.trace(message.strip())

    def _log_state(self):
        # TODO: refactor
        if self.logger.log_level > self.logger.LogLevel.DEBUG:
            return

        if self.processor.is_live and self.processor.post_live:
            live_message = f'post_live ({self.processor.live_segment_target_duration_sec}s)'
        elif self.processor.is_live:
            live_message = f'live ({self.processor.live_segment_target_duration_sec}s)'
        else:
            live_message = 'not_live'

        if self.processor.is_live:
            live_message += ' bid:' + str_or_none(broadcast_id_from_url(self.url))

        consumed_ranges_message = (
            ', '.join(
                f'{izf.format_id.itag}:'
                + ', '.join(
                    f'{cf.start_sequence_number}-{cf.end_sequence_number} '
                    f'({cf.start_time_ms}-'
                    f'{cf.start_time_ms + cf.duration_ms})'
                    for cf in izf.consumed_ranges
                )
                for izf in self.processor.initialized_formats.values()
            ) or 'none'
        )

        izf_parts = []
        for izf in self.processor.initialized_formats.values():
            s = f'{izf.format_id.itag}'
            if izf.discard:
                s += 'd'
            p = []
            if izf.total_segments:
                p.append(f'{izf.total_segments}')
            if izf.sequence_lmt is not None:
                p.append(f'lmt={izf.sequence_lmt}')
            if p:
                s += ('(' + ','.join(p) + ')')
            izf_parts.append(s)

        initialized_formats_message = ', '.join(izf_parts) or 'none'

        unknown_part_message = ''
        if self._unknown_part_types:
            unknown_part_message = 'unkpt:' + ', '.join(part_type.name for part_type in self._unknown_part_types)

        sabr_context_update_msg = ''
        if self.processor.sabr_context_updates:
            sabr_context_update_msg += 'cu:[' + ','.join(
                f'{k}{"(n)" if k not in self.processor.sabr_contexts_to_send else ""}'
                for k in self.processor.sabr_context_updates
            ) + ']'

        self.logger.debug(
            "[SABR State] "
            f"v:{self.processor.video_id or 'unknown'} "
            f"c:{self.processor.client_info.client_name.name} "
            f"t:{self.processor.client_abr_state.player_time_ms} "
            f"td:{self.processor.total_duration_ms if self.processor.total_duration_ms else 'n/a'} "
            f"h:{urllib.parse.urlparse(self.url).netloc} "
            f"exp:{dt.timedelta(seconds=int(self._gvs_expiry() - time.time())) if self._gvs_expiry() else 'n/a'} "
            f"rn:{self._request_number} rnns:{self._no_new_segments_tracker.consecutive_requests} "
            f"lnns:{self._no_new_segments_tracker.live_head_segment_started or 'n/a'} "
            f"mmb:{self._sq_mismatch_backtrack_count} mmf:{self._sq_mismatch_forward_count} "
            f"pot:{'Y' if self.processor.po_token else 'N'} "
            f"sps:{self.processor.stream_protection_status.name if self.processor.stream_protection_status else 'n/a'} "
            f"{live_message} "
            f"if:[{initialized_formats_message}] "
            f"cr:[{consumed_ranges_message}] "
            f"{sabr_context_update_msg} "
            f"{unknown_part_message}",
        )
