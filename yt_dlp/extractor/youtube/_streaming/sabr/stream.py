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
    BufferedRange,
    CuepointList,
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
    TimeRange,
)
from yt_dlp.networking import Request, Response
from yt_dlp.networking.exceptions import HTTPError, TransportError
from yt_dlp.utils import RetryManager, int_or_none, parse_qs, str_or_none, traverse_obj

from .exceptions import (
    BroadcastIdChanged,
    PoTokenError,
    SabrStreamConsumedError,
    SabrStreamError,
    SabrUrlExpired,
    StreamStallError,
)
from .models import (
    AudioSelector,
    CaptionSelector,
    ConsumedRange,
    InitializedFormat,
    PoTokenStatus,
    ReloadConfigReason,
    SabrLogger,
    VideoSelector,
)
from .part import (
    FormatInitializedSabrPart,
    LiveStateSabrPart,
    MediaSeekSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
    MediaSegmentInitSabrPart,
    PoTokenStatusSabrPart,
)
from .processor import SabrProcessor, build_vpabr_request
from .utils import (
    broadcast_id_from_url,
    fallback_gvs_url,
    find_consumed_range_by_time,
    find_consumed_range_chain,
    validate_sabr_url,
)
from ..ump import UMPDecoder, UMPPart, UMPPartId, read_varint

DEFAULT_HTTP_RETRIES = 10
DEFAULT_POT_RETRIES = 5
DEFAULT_HOST_FALLBACK_THRESHOLD = 8
DEFAULT_MAX_EMPTY_REQUESTS = 3
DEFAULT_MIN_LIVE_END_WAIT_SEC = 10

# Window at the head of the live stream to allow a stall to be recognized as a stream end.
# Sometimes there are unreachable segments at the end of the livestream.
# Current observations suggest a segment tolerance of 4 is sufficient.
#
# Note it might be possible to calculate this dynamically from the difference between
# the head sequence time and max seekable time. However, for now it is sufficient to hardcode.
DEFAULT_LIVE_END_SEGMENT_TOLERANCE = 4
DEFAULT_EXPIRY_THRESHOLD_SEC = 60

# YouTube allows retrieval of segments max 7 days.
# -1 hour leeway added for stability
DEFAULT_MAX_REWIND_TIME_MS = (7 * 24 * 3600 * 1000) - 3600


@dataclasses.dataclass
class StreamStallTracker:
    stalled_requests: int = 0
    # note: lambda to allow mocking of time in tests
    last_active_time: float = dataclasses.field(default_factory=lambda: time.time())  # noqa: PLW0108
    # Whether the last request resulted in any activity (new segments)
    activity_detected: bool = False

    def register_activity(self):
        self.stalled_requests = 0
        self.last_active_time = time.time()
        self.activity_detected = True

    def register_stall(self):
        if not self.activity_detected:
            self.stalled_requests += 1

    def next_request(self):
        self.activity_detected = False


@dataclasses.dataclass
class Heartbeat:
    is_live: bool
    video_id: str
    broadcast_id: str | None


@dataclasses.dataclass
class ReloadConfigRequest:
    reason: ReloadConfigReason
    reload_playback_token: str | None = None


@dataclasses.dataclass
class ReloadConfigResponse:
    video_playback_ustreamer_config: str
    server_abr_streaming_url: str
    client_info: ClientInfo
    video_id: str | None = None
    po_token: str | None = None
    heartbeat_callback: HeartbeatCallback | None = None
    pot_callback: PotCallback | None = None
    reload_callback: ReloadCallback | None = None


if typing.TYPE_CHECKING:
    ReloadCallback = typing.Callable[[ReloadConfigRequest], ReloadConfigResponse | None]
    PotCallback = typing.Callable[[PoTokenStatus], str | None]
    HeartbeatCallback = typing.Callable[[], Heartbeat | None]
    SabrPartType = MediaSegmentInitSabrPart | MediaSegmentDataSabrPart | MediaSegmentEndSabrPart | FormatInitializedSabrPart | PoTokenStatusSabrPart | MediaSeekSabrPart | LiveStateSabrPart
    IterPartsType = typing.Generator[SabrPartType, None, None]


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
    @param live_end_segment_tolerance: The number of segments before the live head segment at which the livestream is allowed to end. Defaults to 3.
    @param post_live: Whether the live stream is in post-live mode. Used to determine how to handle the end of the stream.
    @param video_id: The video ID of the YouTube video. Used for validating received data is for the correct video.
    @param retry_sleep_func: A function to calculate sleep time between retries. Takes the retry count as an argument.
    @param expiry_threshold_sec: The number of seconds before the GVS expiry to consider it expired. Defaults to 1 minute.
    @param heartbeat_callback: A function called to check if the stream is still active before ending.
    @param pot_callback: A function called to retrieve a new PO Token.
    @param reload_callback: A function called to reload the SABR configuration, such as on SABR URL expiry.


    Yielded parts:
    - FormatInitializedSabrPart
    - MediaSegmentInitSabrPart
    - MediaSegmentDataSabrPart
    - MediaSegmentEndSabrPart
    - PoTokenStatusSabrPart
    - MediaSeekSabrPart
    - LiveStateSabrPart
    """

    # Parts to ignore from the state debug log
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
        UMPPartId.SNACKBAR_MESSAGE,
    )

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
        retry_sleep_func: typing.Callable[[int], int] | None = None,
        expiry_threshold_sec: int | None = None,
        heartbeat_callback: HeartbeatCallback | None = None,
        pot_callback: PotCallback | None = None,
        reload_callback: ReloadCallback | None = None,
        enable_live_deep_rewind: bool | None = None,
    ):

        self.logger = logger
        self._urlopen = urlopen
        self._heartbeat_callback = heartbeat_callback
        self._pot_callback = pot_callback
        self._reload_callback = reload_callback

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
        self.http_retries = http_retries or DEFAULT_HTTP_RETRIES
        self.pot_retries = pot_retries or DEFAULT_POT_RETRIES
        self.host_fallback_threshold = host_fallback_threshold or DEFAULT_HOST_FALLBACK_THRESHOLD
        self.max_empty_requests = max_empty_requests or DEFAULT_MAX_EMPTY_REQUESTS
        self.live_end_wait_sec = live_end_wait_sec or max(DEFAULT_MIN_LIVE_END_WAIT_SEC, self.max_empty_requests * self.processor.live_segment_target_duration_sec)
        self.live_end_segment_tolerance = live_end_segment_tolerance or DEFAULT_LIVE_END_SEGMENT_TOLERANCE
        self.enable_live_deep_rewind = enable_live_deep_rewind or False
        self.expiry_threshold_sec = expiry_threshold_sec or DEFAULT_EXPIRY_THRESHOLD_SEC
        if self.expiry_threshold_sec <= 0:
            raise ValueError('expiry_threshold_sec must be greater than 0')
        if self.max_empty_requests <= 0:
            raise ValueError('max_empty_requests must be greater than 0')
        self.retry_sleep_func = retry_sleep_func
        self._request_number = 0

        # Keep track if we got any new (not consumed) segments in the request.
        self._stream_stall_tracker = StreamStallTracker()
        self._next_request_wait_sec = 0
        self._sps_retry_manager: typing.Generator | None = None
        self._current_sps_retry = None
        self._http_retry_manager: typing.Generator | None = None
        self._current_http_retry = None
        self._unknown_part_types = set()

        self._last_vpabr = None

        # Whether the current request is a result of a retry
        self._is_retry = False

        self._consumed = False

        # Buffered ranges to be injected in the next request
        self._injected_consumed_ranges = []

    def close(self):
        self._consumed = True

    def __iter__(self):
        return self.iter_parts()

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        validate_sabr_url(url)
        if hasattr(self, '_url'):
            self._process_broadcast_id(broadcast_id_from_url(url))
        self._url = url
        if str_or_none(parse_qs(url).get('source', [None])[0]) in ('yt_live_broadcast', 'yt_premiere_broadcast'):
            self.processor.is_live = True

    @property
    def broadcast_id(self):
        return broadcast_id_from_url(self.url)

    def _process_broadcast_id(self, bid: str | None):
        # Validate a retrieved broadcast ID matches what this stream expects
        if not self.processor.is_live or bid is None or self.broadcast_id is None:
            return

        if bid != self.broadcast_id:
            raise BroadcastIdChanged(self.broadcast_id, bid)

    def iter_parts(self) -> IterPartsType:
        if self._consumed:
            raise SabrStreamConsumedError('SABR stream has already been consumed')

        self._http_retry_manager = None
        self._sps_retry_manager = None

        def report_retry(err, count, retries, fatal=True):
            if count >= self.host_fallback_threshold and isinstance(err, (HTTPError, TransportError)):
                self._process_fallback_server()
            RetryManager.report_retry(
                err, count, retries, info=self.logger.info,
                warn=lambda msg: self.logger.warning(f'Got error: {msg}'),
                error=None if fatal else lambda msg: self.logger.warning(f'Got error: {msg}'),
                sleep_func=self.retry_sleep_func,
            )

        def report_sps_retry(err, count, retries, fatal=True):
            RetryManager.report_retry(
                err, count, retries, info=self.logger.info,
                warn=lambda msg: self.logger.warning(f'Got error: {msg}'),
                error=None if fatal else lambda msg: self.logger.warning(f'Got error: {msg}'),
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
            self._process_next_wait()

            self._process_expiry()
            vpabr = self._apply_injected_consumed_ranges(build_vpabr_request(self.processor))
            self._last_vpabr = vpabr

            payload = protobug.dumps(vpabr)
            self.logger.trace(f'Ustreamer Config: {self.processor.video_playback_ustreamer_config}')
            self.logger.trace(f'Sending SABR request: {vpabr}')

            self._stream_stall_tracker.next_request()

            response = None
            try:
                self._request_number += 1
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
            except TransportError as e:
                self._current_http_retry.error = e
            except HTTPError as e:
                e.close()
                # retry on 5xx errors only
                if 500 <= e.status < 600:
                    self._current_http_retry.error = e
                elif e.status == 403 and self._has_expired():
                    raise SabrUrlExpired from e
                else:
                    raise SabrStreamError(f'HTTP Error: {e.status} - {e.reason}') from e

            if response:
                try:
                    yield from self._parse_ump_response(response)
                except TransportError as e:
                    self._current_http_retry.error = e
                finally:
                    if not response.closed:
                        response.close()

            self._finish_response_processing()
            self._process_sps_retry()

            if not self._current_http_retry.error:
                self._http_retry_manager = None

            if not self._current_sps_retry.error:
                self._sps_retry_manager = None

            retry_next_request = bool(self._current_http_retry.error or self._current_sps_retry.error)

            # We are expecting to stay in the same place for a retry
            if not retry_next_request:
                self._process_next_player_time()
                self._process_live_wait()

                # TODO: should prevent waiting and post_live end of stream check if rewinding still
                self._process_live_deep_rewind()

                self._check_end_of_stream()
                self._check_stream_stall()

                # Request successfully processed, next request is not a retry
                self._is_retry = False
            else:
                self._is_retry = True
                self._check_retry_live_stream_end()

            self.processor.clear_old_cuepoints()

        self._consumed = True
        self._log_state()

    def _process_sps_retry(self):
        # The PO Token may be updated during the request.
        # For logging purposes, the error is determined by the state at the time of the last request.
        error = PoTokenError(missing=not self._last_vpabr.streamer_context.po_token)

        if self.processor.stream_protection_status == StreamProtectionStatus.Status.ATTESTATION_REQUIRED:
            # Always start retrying immediately on ATTESTATION_REQUIRED
            self._current_sps_retry.error = error
            return

    def _process_next_wait(self):
        if self._next_request_wait_sec > 0:
            self.logger.debug(f'Sleeping for {self._next_request_wait_sec} seconds before next request')
            time.sleep(self._next_request_wait_sec)
            self._next_request_wait_sec = 0

    def _wait_for(self, seconds: int):
        self._next_request_wait_sec = max(self._next_request_wait_sec, seconds)

    def _finish_response_processing(self):
        if not len(self.processor.partial_segments):
            return
        msg = 'Received partial segments: ' + ', '.join(
            f'{seg.format_id}: {seg.sequence_number}'
            for seg in self.processor.partial_segments.values()
        )
        self.logger.debug(msg)
        self.processor.partial_segments.clear()

    # region: UMP Part Processors

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
                self._process_reload_player_response(part)
            elif part.part_id == UMPPartId.CUEPOINT_LIST:
                self._process_cuepoint_list(part)
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
        result = self.processor.process_media_header(media_header)
        if result.sabr_part:
            yield result.sabr_part

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
            self._stream_stall_tracker.register_activity()

        if result.sabr_part:
            yield result.sabr_part

    def _process_live_metadata(self, part: UMPPart):
        live_metadata = protobug.load(part.data, LiveMetadata)
        self._log_part(part, protobug_obj=live_metadata)
        result = self.processor.process_live_metadata(live_metadata)
        yield from result.seek_sabr_parts
        if result.live_state_part:
            yield result.live_state_part

    def _process_stream_protection_status(self, part: UMPPart):
        sps = protobug.load(part.data, StreamProtectionStatus)
        self._log_part(part, msg=f'Status: {StreamProtectionStatus.Status(sps.status).name}', protobug_obj=sps)
        result = self.processor.process_stream_protection_status(sps)
        if not result.sabr_part:
            return

        status = result.sabr_part.status
        if status in (
            PoTokenStatus.INVALID,
            PoTokenStatus.PENDING,
            PoTokenStatus.MISSING,
            PoTokenStatus.PENDING_MISSING,
        ):
            po_token = self._fetch_pot(status)
            if po_token is not None:
                self.logger.debug('Fetched new PO Token')
                self.processor.po_token = po_token

        if result.sabr_part:
            yield result.sabr_part

    def _process_sabr_redirect(self, part: UMPPart):
        sabr_redirect = protobug.load(part.data, SabrRedirect)
        self._log_part(part, protobug_obj=sabr_redirect)
        self.url = sabr_redirect.redirect_url
        self.logger.debug(f'Redirecting to {self.url}')

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
        self._reload_config(
            reason=ReloadConfigReason.SABR_RELOAD_PLAYER_RESPONSE,
            reload_playback_token=reload_player_response.reload_playback_params.token)

    def _process_cuepoint_list(self, part: UMPPart):
        cuepoint_list = protobug.load(part.data, CuepointList)
        self._log_part(part, protobug_obj=cuepoint_list)
        self.processor.process_cuepoint_list(cuepoint_list)

    # endregion

    def _process_fallback_server(self):
        # Attempt to fall back to another GVS host in the case the current one fails
        new_url = fallback_gvs_url(self.url)
        if not new_url:
            self.logger.debug('No more fallback hosts available')
            return

        self.logger.warning(f'Falling back to host {urllib.parse.urlparse(new_url).netloc}')
        self.url = new_url

    def _gvs_expiry(self):
        return int_or_none(traverse_obj(parse_qs(self.url), ('expire', 0), get_all=False))

    def _process_expiry(self):
        expires_at = self._gvs_expiry()

        if not expires_at:
            self.logger.warning(
                'No expiry timestamp found in URL. Will not be able to refresh.', once=True)
            return

        if expires_at - self.expiry_threshold_sec >= time.time():
            self.logger.trace(f'URL expires in {int(expires_at - time.time())} seconds')
            return

        self.logger.debug(
            f'Requesting config refresh as the URL is due to expire within {self.expiry_threshold_sec} seconds')
        self._reload_config(reason=ReloadConfigReason.SABR_URL_EXPIRY)

    def _has_expired(self):
        expires_at = self._gvs_expiry()
        if not expires_at:
            return False
        return self._gvs_expiry() <= time.time()

    def _reload_config(self, reason: ReloadConfigReason, reload_playback_token: str | None = None):
        response = self._fetch_reloaded_config(reason, reload_playback_token)
        if response is None:
            return

        self.url = response.server_abr_streaming_url
        self.processor.video_playback_ustreamer_config = response.video_playback_ustreamer_config
        self.processor.client_info = response.client_info

        if response.po_token is not None:
            self.processor.po_token = response.po_token

        # Clear ad contexts as the ids will no longer be valid
        self.processor.sabr_context_updates.clear()
        self.processor.sabr_contexts_to_send.clear()
        self.processor.ad_cuepoints.clear()

        if response.reload_callback:
            self._reload_callback = response.reload_callback
        if response.pot_callback:
            self._pot_callback = response.pot_callback
        if response.heartbeat_callback:
            self._heartbeat_callback = response.heartbeat_callback

        self.logger.debug('Reloaded SABR config')

    # region: Stream progression

    def _process_next_player_time(self):
        # 1. If any enabled format selector does not have an initialized format, skip
        if self._missing_initialized_format():
            self.logger.debug(
                'Skipping player time increment; not all enabled format selectors have an initialized format yet')
            return

        # 2. If the format is seeking, skip as player time should not progress while seeking
        # NOTE: excluding if seek_ms is within a consumed range chain for the initialized format,
        #  otherwise stream can get stuck in some circumstances
        live_tolerance_ms = self.processor.live_segment_target_duration_tolerance_ms if self.processor.is_live else 0
        if any(
            izf.seek_ms is not None
            and not find_consumed_range_by_time(izf.seek_ms, izf.consumed_ranges, live_tolerance_ms)
            for izf in self._active_initialized_formats()
        ):
            self.logger.debug(
                'Skipping player time increment; one or more initialized formats are currently seeking')
            return

        # 3. If missing a consumed range for the current player time, skip
        current_consumed_ranges = self._current_consumed_ranges()
        if any(
            cr is None for _, cr in current_consumed_ranges
        ):
            self.logger.debug(
                'Skipping player time increment; one or more initialized formats '
                'is missing a consumed range for current player time')
            return

        # 4. Update player time to the lowest end time of consumed ranges that match the current player time
        min_izf, min_cr = self._get_min_consumed_range(current_consumed_ranges)
        min_consumed_time_ms = min_cr.start_time_ms + min_cr.duration_ms
        self.logger.trace(f'Lowest consumed range: format={min_izf.format_id}, cr={min_cr} (end={min_consumed_time_ms}ms)')

        difference = min_consumed_time_ms - self.processor.player_time_ms
        self.processor.player_time_ms = min_consumed_time_ms
        self.logger.trace(f'Updated player time ms to: {self.processor.player_time_ms} (+{difference}ms)')

    # endregion

    # region: live deep rewind
    def _process_live_deep_rewind(self):
        # EXPERIMENTAL
        # BEWARE: super janky code
        # TODO: check how post_live behaves
        if (
            not self.processor.is_live
            or not self.enable_live_deep_rewind
            or self._missing_initialized_format()
        ):
            return

        max_seekable_time_ms: int | None = getattr(self.processor.live_state, 'max_seekable_time_ms', None)
        min_seekable_time_ms: int | None = getattr(self.processor.live_state, 'min_seekable_time_ms', None)
        # TODO: for non-DVR, min seekable ends up being the first-deep reminded segment, so this detection doesn't work
        if max_seekable_time_ms is None or min_seekable_time_ms is None:
            self.logger.debug('cannot deep rewind: max_seekable_time_ms/min_seekable_time_ms is unavailable')
            # TODO: seek to an expected segment and ensure that is validated
            for izf in self._active_initialized_formats():
                izf.seek_ms = 0
            return

        # TODO: temp solution to constant seeking and creating lots of new buffered ranges due to our anchor lagging behind DVR lower bound.
        #  Should probably allow anchor to catch up by multiple segments at a time?
        max_buffer_size = max_seekable_time_ms - min_seekable_time_ms
        buffer = min(max_buffer_size, 20 * (self.processor.live_segment_target_duration_sec * 1000))
        if min_seekable_time_ms is not None and self.processor.player_time_ms < min_seekable_time_ms + buffer:
            self.logger.debug(f'deep rewind skipped: allowing player time to get ahead of the lower bound by {buffer}ms')
            # TODO: seek to an expected segment and ensure that is validated
            for izf in self._active_initialized_formats():
                izf.seek_ms = 0
            return

        rewind_time_ms = max(0, self.processor.start_time_ms, max_seekable_time_ms - DEFAULT_MAX_REWIND_TIME_MS)
        if rewind_time_ms >= self.processor.player_time_ms:
            self.logger.trace(
                f'skipping deep rewind: player_time_ms={self.processor.player_time_ms} is before rewind_time_ms={rewind_time_ms}')
            return

        estimated_rewind_segment = max(0, (rewind_time_ms // (self.processor.live_segment_target_duration_sec * 1000)) - 1)

        injected_ranges = []
        for izf in self._active_initialized_formats():
            # Find last consumed range in cr chain at rewind_time_ms
            tolerance_ms = self.processor.live_segment_target_duration_tolerance_ms
            rewind_cr = find_consumed_range_by_time(
                # When rewinding to 0, we cannot get segment 0, so it is expected there will not be a consumed range there.
                time_ms=rewind_time_ms + (self.processor.live_segment_target_duration_sec * 1000),
                consumed_ranges=izf.consumed_ranges,
                tolerance_ms=tolerance_ms)

            # If cannot find by time, try by the estimated segment:
            # TODO: maybe use a bigger tolerance when trying to rewind as the estimate could be quite far off
            if not rewind_cr:
                chains = find_consumed_range_chain(estimated_rewind_segment + 1, izf.consumed_ranges)
                if chains:
                    rewind_cr = chains[-1]

            # This range MUST be added to the end of buffered ranges.
            # The start_time_ms MUST be the same as player_time_ms
            self.logger.trace(f'rewind cr: {rewind_cr}, est rewind segment: {estimated_rewind_segment}')
            injected_ranges.append((izf.format_id, ConsumedRange(
                start_time_ms=self.processor.player_time_ms,
                duration_ms=0,
                start_sequence_number=None,
                end_sequence_number=estimated_rewind_segment if rewind_cr is None else rewind_cr.end_sequence_number,
            )))

            # Must mark format as seeking backwards otherwise will get segment mismatch error
            # TODO: add validation whether we got next segment at the player time OR at the rewind target CR.
            izf.seek_ms = 0

        # Store injected ranges for the next request
        if injected_ranges:
            self._injected_consumed_ranges.extend(injected_ranges)
            # Calculate hours from rewind_time_ms
            hours = (max_seekable_time_ms - rewind_time_ms) // 3600000
            # TODO: once=true is not sufficient here, as the hours will change.
            #  An event should be pushed up to the FD and logged there.
            self.logger.warning(f'Attempting to deep-rewind up to {hours} hour(s)', once=True)

    def _apply_injected_consumed_ranges(self, vpabr):
        if not self._injected_consumed_ranges:
            return vpabr

        for format_id, cr in self._injected_consumed_ranges:
            vpabr.buffered_ranges.append(
                BufferedRange(
                    format_id=format_id,
                    start_segment_index=cr.start_sequence_number,
                    end_segment_index=cr.end_sequence_number,
                    start_time_ms=cr.start_time_ms,
                    duration_ms=cr.duration_ms,
                    time_range=TimeRange(
                        start_ticks=cr.start_time_ms,
                        duration_ticks=cr.duration_ms,
                        timescale=1000,
                    ),
                ))

        self.logger.trace(f'Injected {len(self._injected_consumed_ranges)} consumed ranges into vpabr')
        if self.logger.log_level == self.logger.LogLevel.TRACE:
            self.logger.trace(f'Injected consumed ranges: {self._injected_consumed_ranges}')

        # TODO: clear here or after successful request?
        # Could be useful to clear on bad request to try recover the stream
        self._injected_consumed_ranges = []
        return vpabr
    # endregion

    def _process_live_wait(self):
        if not self.processor.is_live or self.processor.post_live:
            # Does not apply for post live as all segments should be available
            return

        max_seekable_time_ms = getattr(self.processor.live_state, 'max_seekable_time_ms', None)

        if max_seekable_time_ms is None:
            # fallback to live head
            max_seekable_time_ms = getattr(self.processor.live_state, 'head_sequence_time_ms', None)

        if max_seekable_time_ms is not None and self.processor.player_time_ms >= max_seekable_time_ms:
            # If we are far past the max seekable time ms, move the player time backwards.
            # This can occur if initially request a start time well past the head and no server seek occurs.
            #
            # Note: Sometimes the max seekable time in the live metadata may decrease (usually temporary).
            # To avoid accidently requesting segments before the current consumed range,
            # we set the minimum player time to the end of that consumed range.
            #
            # player time: | ------------- OK ------------- | ------ too far ahead, rollback to 2) ------>
            #      1. max_seekable          2. max_seekable + est. seg duration
            min_pair = self._get_min_consumed_range(self._current_consumed_ranges())
            min_consumed_time_ms = 0
            if min_pair:
                min_consumed_time_ms = min_pair[1].start_time_ms + min_pair[1].duration_ms

            new_time = max(
                min_consumed_time_ms,
                min(self.processor.player_time_ms, max_seekable_time_ms + (self.processor.live_segment_target_duration_sec * 1000) - self.processor.live_segment_target_duration_tolerance_ms))

            if new_time != self.processor.player_time_ms:
                self.logger.trace(
                    f'Setting player time to: '
                    f'{new_time}ms (-{self.processor.player_time_ms - new_time}ms)')
                self.processor.player_time_ms = new_time

            # Wait for next segments to be available.
            # NOTE: If live metadata is not available, we have no way of knowing if we need to wait
            # for the next segment or are midway for the stream.
            # In this case, the stream stall logic will trigger a wait if we get no new segments.
            next_request_backoff_ms = getattr(self.processor.next_request_policy, 'backoff_time_ms', None) or 0
            wait_seconds = max(next_request_backoff_ms // 1000, self.processor.live_segment_target_duration_sec)
            self._wait_for(wait_seconds)

    # endregion

    # region: End of stream detection

    def _check_end_of_stream(self):
        if self.processor.is_live and not self.processor.post_live:
            # Livestream end detection handled as part of stream stall detection
            # Post-live is handled by both - depending on if we can get the final segments or not
            return

        # Ensure all enabled format selectors have an initialized format
        # otherwise we cannot determine end of stream yet
        if self._missing_initialized_format():
            self.logger.debug(
                'Skipping end of stream check; not all enabled format selectors have an initialized format yet')
            return

        # Also check if player time is at the head of the stream for post-live
        #  (max_seekable_time_ms == head_sequence_time_ms for post-live)
        if self._is_at_end_of_vod_stream() or self._player_time_near_live_head(tolerant=False):
            self.logger.debug('End of stream')
            self._consumed = True
            return

    def _is_at_end_of_vod_stream(self):
        player_time_ms = self.processor.player_time_ms

        # 1. All enabled formats have a consumed range for the current player time,
        #  and they are all at the end of their consumed ranges.
        if all(
            cr is not None and izf.last_segment_number is not None and cr.end_sequence_number >= izf.last_segment_number
            for izf, cr in self._current_consumed_ranges()
        ):
            self.logger.trace(
                f'All enabled formats have reached their last expected segment '
                f'at player time {player_time_ms} ms, assuming end of vod.')
            return True

        # 2. Fallback: check if the player time exceeds the end time of all enabled formats
        # Note: this will not apply for post-live as end_time_ms is not available.
        if all(
            izf.end_time_ms and player_time_ms >= izf.end_time_ms
            for izf in self._active_initialized_formats()
        ):
            self.logger.trace(
                f'All enabled formats have reached their end time by player time {player_time_ms} ms, '
                f'assuming end of vod.')
            return True

        return False

    def _check_retry_live_stream_end(self):
        # For live and post-live, if:
        # - on last http retry
        # - and stream is near the head
        # - and the live stream is no longer live (or is post-live)
        # then mark the stream as consumed rather than failing.
        # Sometimes the last segment or two of a live stream is unavailable and get a read error.
        if (
            not self.processor.is_live or not self._is_retry
            or not self._current_http_retry
            or self._current_http_retry.attempt <= self.http_retries
        ):
            return

        last_retry_msg = '; not marking stream as consumed on last retry'
        is_near_live_head = self._is_near_head_of_live_stream()
        if not is_near_live_head:
            context_msg = 'Not near live stream head' if self.processor.live_state else 'No live metadata available'
            self.logger.debug(context_msg + last_retry_msg)
            return

        if self._missing_initialized_format():
            self.logger.debug('Not all enabled format selectors have an initialized format yet' + last_retry_msg)
            return

        if not self.processor.post_live and self._heartbeat_is_live() is not False:
            self.logger.debug(
                'Heartbeat does not indicate stream has finished' + last_retry_msg)
            return

        self.logger.debug(
            'Retry attempts exceeded, but near the live stream head and live stream has ended. '
            'Assuming reached end of stream.')
        self._consumed = True

    # endregion

    # region: Stream Stall Detection
    def _check_stream_stall(self):
        if self.processor.is_live:
            return self._check_live_stream_stall()

        return self._check_vod_stream_stall()

    def _update_stall(self):
        self.logger.debug(
            f'No activity detected in request {self._request_number}; '
            f'registering stall (count: {self._stream_stall_tracker.stalled_requests + 1})')
        self._stream_stall_tracker.register_stall()

    def _check_vod_stream_stall(self):
        if not self._stream_stall_tracker.activity_detected:
            self._update_stall()
            self._check_vod_ad_wait()

        if self._stream_stall_tracker.stalled_requests >= self.max_empty_requests:
            raise StreamStallError(
                f'Stream stalled; no activity detected in {self.max_empty_requests} consecutive requests')

    def _check_vod_ad_wait(self):
        # xxx: this logic is fairly loose, could do with some tightening
        if (
            self.processor.next_request_policy and self.processor.next_request_policy.backoff_time_ms
            and any(t in self.processor.sabr_contexts_to_send for t in self.processor.sabr_context_updates)
        ):
            wait_seconds = math.ceil(self.processor.next_request_policy.backoff_time_ms / 1000)
            # TODO: consider logging this in the FD
            self.logger.info(f'Sleeping {wait_seconds:.2f} seconds as required by the server')
            self._wait_for(wait_seconds)

    def _check_live_stream_stall(self):
        # Two conditions to consider for stalled live stream:
        # 1. No activity midway through stream (unexpected)
        # 2. No activity at or near the end of the stream (expected, mark stream as ended)

        # Notes:
        # - Sometimes the last segment we can retrieve is a couple segments behind the live head.

        if not self._stream_stall_tracker.activity_detected:
            self._update_stall()

        empty_requests = self._stream_stall_tracker.stalled_requests
        max_requests_reached = empty_requests >= self.max_empty_requests
        seconds_since_last_activity = time.time() - self._stream_stall_tracker.last_active_time
        live_end_wait_time_exceeded = seconds_since_last_activity >= self.live_end_wait_sec

        if not max_requests_reached or not live_end_wait_time_exceeded:
            self.logger.trace(
                f'Stall check skipped. '
                f'Seconds since last activity: {seconds_since_last_activity:.2f}s (exceeded={live_end_wait_time_exceeded}). '
                f'Empty requests: {empty_requests} (exceeded max={max_requests_reached}).')
            if empty_requests >= 1:
                # Sometimes we can't get the head segment - rather tend to sit behind the head segment for the duration of the livestream.
                # We should also slow down and wait if getting empty requests midway through.
                self._wait_for(max(self._next_request_backoff_ms() // 1000, self.processor.live_segment_target_duration_sec))
            return

        # If LIVE_METADATA is not provided, we cannot be sure if we are at the head of the stream.
        # To allow the stream to end, consider it as near live head in this case.
        # This has been seen on ANDROID_VR client.
        is_near_live_head = self._is_near_head_of_live_stream()
        if is_near_live_head or not self.processor.live_state:
            context_msg = 'Near live stream head' if is_near_live_head else 'No live metadata available'

            # TODO: add a timeout on how long heartbeat can indicate it is still live
            heartbeat_is_live = self._heartbeat_is_live()
            if heartbeat_is_live:
                self.logger.debug(
                    f'No activity detected in {empty_requests} requests and {seconds_since_last_activity:.1f} seconds. '
                    f'{context_msg} but heartbeat indicates stream is still live; continuing to wait for segments.')
                return

            # In the case we only get one format at the start of a stream and stall, it should fail with a stall
            # However, if the livestream has definitely ended, this could occur if started download at the end of a non-DVR stream.
            if self._missing_initialized_format() and heartbeat_is_live is not False:
                self.logger.debug(
                    'Skipping end of live stream check; not all enabled format selectors have an initialized format yet')
            else:
                self.logger.debug(
                    f'No activity detected in {empty_requests} requests and {seconds_since_last_activity:.1f} seconds. '
                    f'{context_msg} and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
                self._consumed = True
                return

        not_near_head_suffix = ' and not near live head.' if not is_near_live_head else '.'
        raise StreamStallError(
            f'Stream stalled; no activity detected in '
            f'{empty_requests} requests and {seconds_since_last_activity:.1f} seconds'
            f'{not_near_head_suffix}')

    # endregion

    def _active_initialized_formats(self):
        return (
            izf for izf in self.processor.initialized_formats.values()
            if not izf.discard
        )

    def _next_request_backoff_ms(self):
        backoff_ms = 0
        if self.processor.next_request_policy and self.processor.next_request_policy.backoff_time_ms:
            backoff_ms = self.processor.next_request_policy.backoff_time_ms
        return backoff_ms

    def _current_consumed_ranges(self) -> list[tuple[InitializedFormat, ConsumedRange | None]]:
        current = []
        tolerance = self.processor.live_segment_target_duration_tolerance_ms if self.processor.is_live else 0
        for izf in self._active_initialized_formats():
            cr = find_consumed_range_by_time(
                self.processor.player_time_ms,
                izf.consumed_ranges,
                tolerance_ms=tolerance,
            )
            current.append((izf, cr))
        return current

    def _get_min_consumed_range(self, current_consumed_ranges: list[tuple[InitializedFormat, ConsumedRange | None]]):
        consumed_ranges = list(filter(lambda pair: pair[1] is not None, current_consumed_ranges))
        if not consumed_ranges:
            return None
        return min(
            consumed_ranges, key=lambda pair: pair[1].start_time_ms + pair[1].duration_ms)

    def _is_near_head_of_live_stream(self):
        # 1. Check if near head segment based on consumed segments
        head_sequence_number = getattr(self.processor.live_state, 'head_sequence_number', None)
        if head_sequence_number is not None:
            if all(
                cr is not None and (head_sequence_number - cr.end_sequence_number) <= self.live_end_segment_tolerance
                for izf, cr in self._current_consumed_ranges()
            ):
                self.logger.trace(
                    f'Near live stream head detected based on consumed ranges of active formats: '
                    f'head seq ({head_sequence_number}) - tolerance ({self.live_end_segment_tolerance})')
                return True

        # 2. Check if near head sequence based on total duration
        # NOTE: head sequence time is the start time of the head sequence
        return self._player_time_near_live_head(tolerant=True)

    def _heartbeat_is_live(self) -> bool | None:
        if not self.processor.is_live or self.processor.post_live:
            return None

        if not self._heartbeat_callback:
            self.logger.debug('No heartbeat callback provided, skipping heartbeat check')
            return None

        try:
            heartbeat = self._heartbeat_callback()
        except Exception as e:
            self.logger.warning(f'Error occurred while calling heartbeat callback, skipping heartbeat check: {e}')
            return None

        self.logger.trace(f'Heartbeat response: {heartbeat}')

        if not heartbeat:
            self.logger.debug('Heartbeat callback returned no response, skipping heartbeat check')
            return None

        if not isinstance(heartbeat, Heartbeat):
            self.logger.warning('Invalid heartbeat response received, skipping heartbeat check')
            return None

        self._process_broadcast_id(heartbeat.broadcast_id)
        return heartbeat.is_live

    def _fetch_pot(self, status: PoTokenStatus):
        if not self._pot_callback:
            self.logger.debug('No PO Token callback provided, skipping PO Token fetch')
            return None

        try:
            po_token = self._pot_callback(status)
        except Exception as e:
            self.logger.warning(f'Error occurred while calling PO Token callback: {e!r}')
            return None

        if po_token is None:
            self.logger.debug('PO Token callback returned no response')
            return None

        if not isinstance(po_token, str):
            self.logger.warning(f'Invalid PO Token response received: {po_token!r}')
            return None

        return po_token

    def _fetch_reloaded_config(self, reason: ReloadConfigReason, reload_playback_token: str | None = None) -> ReloadConfigResponse | None:
        if not self._reload_callback:
            self.logger.debug('No reload callback provided, skipping config reload')
            return None

        request = ReloadConfigRequest(reason, reload_playback_token)
        try:
            response = self._reload_callback(request)
        except Exception as e:
            self.logger.warning(f'Error occurred while calling reload callback: {e!r}')
            return None

        if response is None:
            self.logger.debug('Reload callback returned no response')
            return None

        if not self._validate_reload_config_response(response):
            return None

        return response

    def _validate_reload_config_response(self, response: ReloadConfigResponse):
        if not isinstance(response, ReloadConfigResponse):
            self.logger.warning(f'Invalid reload response: not a ReloadConfigResponse: {response!r}')
            return False

        for item in ('video_playback_ustreamer_config', 'server_abr_streaming_url'):
            value = getattr(response, item, None)
            if value is None or not isinstance(value, str):
                self.logger.warning(f'Invalid reload response: missing or invalid {item}: {value!r}')
                return False

        client_info = response.client_info
        if client_info is None or not isinstance(client_info, ClientInfo):
            self.logger.warning(f'Invalid reload response: missing or invalid client_info: {client_info!r}')
            return False

        # Only validate the client name; we can reasonably expect the client version to change
        if client_info.client_name != self.processor.client_info.client_name:
            self.logger.warning(
                f'Client name in reload response does not match current client name: '
                f'{client_info.client_name} != {self.processor.client_info.client_name.name}')
            return False

        video_id = response.video_id
        if self.processor.video_id is not None and video_id != self.processor.video_id:
            self.logger.warning(
                f'Video ID in reload response does not match current video ID: {video_id} != {self.processor.video_id}')
            return False

        if response.po_token is not None and not isinstance(response.po_token, str):
            self.logger.warning(f'Invalid reload response: po_token is not a string: {response.po_token!r}')
            return False

        for item in ('heartbeat_callback', 'pot_callback', 'reload_callback'):
            value = getattr(response, item, None)
            if value is not None and not callable(value):
                self.logger.warning(f'Invalid reload response: invalid callback function for {item}: {value!r}')
                return False

        return True

    def _player_time_near_live_head(self, tolerant=False) -> bool:
        # Check if the current player time is near or at the live stream head based on head sequence time
        # with an optional tolerance for considering "near" the head

        player_time_ms = self.processor.player_time_ms
        head_sequence_time_ms = getattr(self.processor.live_state, 'head_sequence_time_ms', None)
        live_segment_target_duration_ms = self.processor.live_segment_target_duration_sec * 1000
        live_segment_duration_tolerance_ms = self.processor.live_segment_target_duration_tolerance_ms
        estimated_head_duration_ms = live_segment_target_duration_ms - live_segment_duration_tolerance_ms
        live_end_tolerance_ms = 0
        if tolerant:
            live_end_tolerance_ms = live_segment_target_duration_ms * self.live_end_segment_tolerance

        if head_sequence_time_ms is not None:
            if player_time_ms >= head_sequence_time_ms + estimated_head_duration_ms - live_end_tolerance_ms:
                self.logger.trace(
                    f'Near or at live stream head detected based on player time '
                    f'and head sequence end time with tolerance (ms): '
                    f'{player_time_ms} >= {head_sequence_time_ms + estimated_head_duration_ms} - {live_end_tolerance_ms}')
                return True
        return False

    def _missing_initialized_format(self):
        return not all(
            any(izf.format_selector is selector for izf in self.processor.initialized_formats.values())
            for selector in self.processor.format_selectors() if not selector.discard_media
        )

    # region: logging
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

    def _stats_live_parts(self):
        parts = []
        if self.processor.is_live:
            if self.processor.post_live:
                parts.append('post_live')
            else:
                parts.append('live')
            parts.append(f'{self.processor.live_segment_target_duration_sec}s')
            parts.append('bid:' + (str_or_none(broadcast_id_from_url(self.url)) or 'n/a'))

            if self.processor.live_state:
                parts.append(f'hs:{self.processor.live_state.head_sequence_number}')
                parts.append(f'hst:{self.processor.live_state.head_sequence_time_ms}')
                parts.append(f'mxt:{self.processor.live_state.max_seekable_time_ms}')
                parts.append(f'mnt:{self.processor.live_state.min_seekable_time_ms}')
        else:
            parts.append('vod')
        return parts

    def _stats_cr_part(self):
        parts = []
        for izf in self.processor.initialized_formats.values():
            segs = ', '.join(
                f'{cf.start_sequence_number}-{cf.end_sequence_number} ({cf.start_time_ms}-{cf.start_time_ms + cf.duration_ms})'
                for cf in izf.consumed_ranges
            )
            parts.append(f'{izf.format_id.itag}:' + (segs or ''))
        message = ', '.join(parts) if parts else 'none'
        return f'cr:[{message}]'

    def _stats_izf_part(self):
        parts = []
        for izf in self.processor.initialized_formats.values():
            s = f'{izf.format_id.itag}'
            if izf.discard:
                s += 'd'
            if izf.seek_ms:
                s += 's'
            p = []
            if izf.last_segment_number:
                p.append(f'{izf.last_segment_number}')
            # TODO: what is sequence_lmt?
            if izf.sequence_lmt is not None:
                p.append(f'lmt={izf.sequence_lmt}')
            if p:
                s += '(' + ','.join(p) + ')'
            parts.append(s)
        message = ', '.join(parts) if parts else 'none'
        return f'if:[{message}]'

    def _stats_unkpt_parts(self):
        if not self._unknown_part_types:
            return []
        return ['unkpt:' + ', '.join(part_type.name for part_type in self._unknown_part_types)]

    def _stats_cu_part(self):
        if not self.processor.sabr_context_updates:
            return ''
        items = []
        for k in self.processor.sabr_context_updates:
            items.append(f'{k}{"(n)" if k not in self.processor.sabr_contexts_to_send else ""}')
        return 'cu:[' + ','.join(items) + ']'

    def _stats_acp_part(self):
        if not self.processor.ad_cuepoints:
            return ''
        return f'acp:{len(self.processor.ad_cuepoints)}'

    def _stats_host_part(self):
        host = urllib.parse.urlparse(self.url).netloc
        return f'h:{host[:-len(".googlevideo.com")]}'

    def _stats_pot_parts(self):
        parts = [f"pot:{'Y' if self.processor.po_token else 'N'}"]
        status = getattr(self.processor.stream_protection_status, 'name', 'n/a')
        parts.append(f'sps:{status}')
        return parts

    def _stats_stall_parts(self):
        return [
            f'sr:{self._stream_stall_tracker.stalled_requests}',
            f'act:{"Y" if self._stream_stall_tracker.activity_detected else "N"}']

    def _stats_exp_part(self):
        expires_at = self._gvs_expiry()
        if expires_at is None:
            return 'exp:n/a'
        expires_in = dt.timedelta(seconds=int(expires_at - time.time()))
        return f'exp:{expires_in}'

    def _player_time_part(self):
        return f't:{self.processor.player_time_ms}' + ('R' if self._injected_consumed_ranges else '')

    def create_stats_str(self):
        parts = [
            f"v:{self.processor.video_id or 'unknown'}",
            f'c:{self.processor.client_info.client_name.name}',
            self._player_time_part(),
            self._stats_host_part(),
            self._stats_exp_part(),
            f'rn:{self._request_number}',
            *self._stats_stall_parts(),
            *self._stats_pot_parts(),
            *self._stats_live_parts(),
            self._stats_izf_part(),
            self._stats_cr_part(),
            self._stats_cu_part(),
            self._stats_acp_part(),
            *self._stats_unkpt_parts(),
        ]
        return ' '.join(filter(None, parts))

    def _log_state(self):
        if self.logger.log_level > self.logger.LogLevel.DEBUG:
            return
        self.logger.debug(f'[SABR State] {self.create_stats_str()}')

    # endregion
