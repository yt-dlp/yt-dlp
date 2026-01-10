from __future__ import annotations
import base64
import dataclasses
import io
import protobug
from yt_dlp import int_or_none
from yt_dlp.extractor.youtube._proto.innertube import NextRequestPolicy
from yt_dlp.extractor.youtube._proto.videostreaming import (
    VideoPlaybackAbrRequest,
    SabrError,
    FormatId,
    FormatInitializationMetadata,
    MediaHeader,
    SabrRedirect,
    SabrContextUpdate,
    SabrContextSendingPolicy,
    StreamProtectionStatus,
)
from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    MediaSegmentInitSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPEncoder, UMPPart, UMPPartId, write_varint
from yt_dlp.networking import Request, Response
from yt_dlp.networking.exceptions import TransportError, HTTPError, RequestError
from yt_dlp.utils import parse_qs

RAW_VIDEO_PLAYBACK_USTREAMER_CONFIG = b'test-config'
VIDEO_PLAYBACK_USTREAMER_CONFIG = base64.urlsafe_b64encode(RAW_VIDEO_PLAYBACK_USTREAMER_CONFIG).decode('utf-8')
VIDEO_ID = 'test_video_id'
DEFAULT_NUM_AUDIO_SEGMENTS = 5
DEFAULT_NUM_VIDEO_SEGMENTS = 10
DEFAULT_MEDIA_SEGMENT_DATA = b'example-media-segment'
DEFAULT_DURATION_MS = 10000
DEFAULT_INIT_SEGMENT_DATA = b'example-init-segment'

DEFAULT_AUDIO_FORMAT = FormatId(itag=140, lmt=123)
DEFAULT_VIDEO_FORMAT = FormatId(itag=248, lmt=456)


def extract_rn(url: str) -> int:
    qs = parse_qs(url)
    return int_or_none(qs.get('rn', ['1'])[0]) or 1


@dataclasses.dataclass
class SabrRequestDetails:
    request: Request
    parts: list = dataclasses.field(default_factory=list)
    response: Response | None = None
    vpabr: VideoPlaybackAbrRequest | None = None
    error: Exception | None = None


class MockBaseIO(io.BytesIO):
    # Raises an error on read at the end of the stream to simulate transport errors.
    _error = None

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, value):
        self._error = value

    def read(self, size=-1):
        data = super().read(size)
        if self._error and (self.tell() == self.getbuffer().nbytes):
            raise self._error
        return data


class SabrRequestHandler:
    def __init__(self, sabr_response_processor: SabrResponseProcessor):
        self.sabr_response_processor = sabr_response_processor
        self.request_history = []

    def send(self, request: Request) -> Response:
        try:
            vpabr, parts, response_code = self.sabr_response_processor.process_request(request.data, request.url, len(self.request_history) + 1)
        except Exception as e:
            self.request_history.append(
                SabrRequestDetails(request=request, error=e))
            raise e

        response_error = None
        fp = MockBaseIO()
        with UMPEncoder(fp) as encoder:
            for part in parts:
                if isinstance(part, Exception):
                    fp.error = part
                    response_error = part
                    parts.remove(part)
                    break
                encoder.write_part(part)

        response = Response(
            url=request.url,
            status=response_code,
            headers={
                'Content-Type': 'application/vnd.yt-ump',
                'Content-Length': str(fp.tell()),
            },
            fp=fp,
        )
        fp.seek(0)

        self.request_history.append(SabrRequestDetails(
            request=request,
            response=response,
            parts=parts,
            error=response_error,
            vpabr=vpabr,
        ))

        return response


class SabrResponseProcessor:

    def __init__(self, options: dict | None = None):
        self.options = options or {}

    def process_request(self, data: bytes, url: str, request_number: int) -> tuple[VideoPlaybackAbrRequest | None, list[UMPPart | Exception], int]:
        try:
            vpabr = protobug.loads(data, VideoPlaybackAbrRequest)
        except Exception:
            error_part = protobug.dumps(SabrError(type='sabr.malformed_request'))
            # TODO: confirm GVS behaviour when VideoPlaybackAbrRequest is malformed
            return None, [UMPPart(data=io.BytesIO(error_part), part_id=UMPPartId.SABR_ERROR, size=len(error_part))], 200

        return vpabr, self.get_parts(vpabr, url, request_number), 200

    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[UMPPart]:
        raise NotImplementedError

    def determine_formats(self, vpabr: VideoPlaybackAbrRequest) -> tuple[FormatId, FormatId]:
        # Check selected_audio_format_ids and selected_video_format_ids
        # TODO: caption format ids, consider initialized_format_ids

        enabled_track_types_bitfield = vpabr.client_abr_state.enabled_track_types_bitfield

        audio_format_id = vpabr.selected_audio_format_ids[0] if vpabr.selected_audio_format_ids else self.options.get('default_audio_format', DEFAULT_AUDIO_FORMAT)
        video_format_id = None

        if enabled_track_types_bitfield != 1:
            video_format_id = vpabr.selected_video_format_ids[0] if vpabr.selected_video_format_ids else self.options.get('default_video_format', DEFAULT_VIDEO_FORMAT)

        return audio_format_id, video_format_id

    def get_format_initialization_metadata_parts(
        self,
        vpabr: VideoPlaybackAbrRequest,
        audio_format_id: FormatId | None = None,
        video_format_id: FormatId | None = None,
        total_audio_segments: int = DEFAULT_NUM_AUDIO_SEGMENTS,
        total_video_segments: int = DEFAULT_NUM_VIDEO_SEGMENTS,
        audio_end_time_ms: int = DEFAULT_DURATION_MS,
        video_end_time_ms: int = DEFAULT_DURATION_MS,
        audio_duration_ms: int = DEFAULT_DURATION_MS,
        video_duration_ms: int = DEFAULT_DURATION_MS,
    ) -> list[UMPPart]:
        parts = []

        audio_buffered_segments = self.buffered_segments(vpabr, total_audio_segments, audio_format_id)
        video_buffered_segments = self.buffered_segments(vpabr, total_video_segments, video_format_id)

        if audio_format_id and not audio_buffered_segments:
            fim = protobug.dumps(FormatInitializationMetadata(
                video_id=VIDEO_ID,
                format_id=audio_format_id,
                mime_type='audio/mp4',
                total_segments=total_audio_segments,
                end_time_ms=audio_end_time_ms,
                duration_ticks=audio_duration_ms,
                duration_timescale=1000,
            ))
            parts.append(UMPPart(
                part_id=UMPPartId.FORMAT_INITIALIZATION_METADATA,
                size=len(fim),
                data=io.BytesIO(fim),
            ))

        if video_format_id and not video_buffered_segments:
            fim = protobug.dumps(FormatInitializationMetadata(
                video_id=VIDEO_ID,
                format_id=video_format_id,
                mime_type='video/mp4',
                total_segments=total_video_segments,
                end_time_ms=video_end_time_ms,
                duration_ticks=video_duration_ms,
                duration_timescale=1000,
            ))
            parts.append(UMPPart(
                part_id=UMPPartId.FORMAT_INITIALIZATION_METADATA,
                size=len(fim),
                data=io.BytesIO(fim),
            ))

        return parts

    def buffered_segments(self, vpabr: VideoPlaybackAbrRequest, total_segments: int, format_id: FormatId):
        return {
            segment_index
            for buffered_range in vpabr.buffered_ranges
            if buffered_range.format_id == format_id
            for segment_index in range(buffered_range.start_segment_index, min(total_segments + 1, buffered_range.end_segment_index + 1))
        }

    def get_init_segment_parts(self, header_id: int, format_id: FormatId):
        media_header = protobug.dumps(MediaHeader(
            header_id=header_id,
            format_id=format_id,
            is_init_segment=True,
            video_id=VIDEO_ID,
            content_length=len(DEFAULT_INIT_SEGMENT_DATA),
        ))

        varint_fp = io.BytesIO()
        write_varint(varint_fp, header_id)
        header_id_varint = varint_fp.getvalue()

        return [
            UMPPart(
                part_id=UMPPartId.MEDIA_HEADER,
                size=len(media_header),
                data=io.BytesIO(media_header),
            ),
            UMPPart(
                part_id=UMPPartId.MEDIA,
                size=len(DEFAULT_INIT_SEGMENT_DATA) + len(header_id_varint),
                data=io.BytesIO(header_id_varint + DEFAULT_INIT_SEGMENT_DATA),
            ),
            UMPPart(
                part_id=UMPPartId.MEDIA_END,
                size=len(header_id_varint),
                data=io.BytesIO(header_id_varint),
            ),
        ]

    def get_media_segments(
        self,
        buffered_segments: set[int],
        total_segments: int,
        max_segments: int,
        player_time_ms: int,
        start_header_id: int,
        format_id: FormatId,
    ) -> tuple[list[UMPPart], int]:

        segment_parts = []

        if not buffered_segments:
            segment_parts.append(self.get_init_segment_parts(header_id=start_header_id, format_id=format_id))

        segment_duration = (DEFAULT_DURATION_MS // total_segments)

        for sequence_number in range(1, total_segments + 1):
            if sequence_number in buffered_segments:
                continue
            if len(segment_parts) >= max_segments:
                break
            start_ms = (sequence_number - 1) * segment_duration
            if start_ms:
                start_ms += 1  # should be + 1 from previous segment end time

            # Basic server-side buffering logic to determine if the segment should be included
            if (
                (player_time_ms >= start_ms + segment_duration)
                or (player_time_ms < (start_ms - segment_duration * 2))  # allow to buffer 2 segments ahead
            ):
                continue

            header_id = len(segment_parts) + start_header_id
            media_header = protobug.dumps(MediaHeader(
                header_id=header_id,
                format_id=format_id,
                video_id=VIDEO_ID,
                content_length=len(DEFAULT_MEDIA_SEGMENT_DATA),
                sequence_number=sequence_number,
                duration_ms=segment_duration,
                start_ms=start_ms,
            ))

            varint_fp = io.BytesIO()
            write_varint(varint_fp, header_id)
            header_id_varint = varint_fp.getvalue()

            segment_parts.append([
                UMPPart(
                    part_id=UMPPartId.MEDIA_HEADER,
                    size=len(media_header),
                    data=io.BytesIO(media_header),
                ),
                UMPPart(
                    part_id=UMPPartId.MEDIA,
                    size=len(DEFAULT_MEDIA_SEGMENT_DATA) + len(header_id_varint),
                    data=io.BytesIO(header_id_varint + DEFAULT_MEDIA_SEGMENT_DATA),
                ),
                UMPPart(
                    part_id=UMPPartId.MEDIA_END,
                    size=len(header_id_varint),
                    data=io.BytesIO(header_id_varint),
                ),
            ])
        return [item for sublist in segment_parts for item in sublist], len(segment_parts) + start_header_id


class BasicAudioVideoProfile(SabrResponseProcessor):
    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[UMPPart]:
        audio_format_id, video_format_id = self.determine_formats(vpabr)
        parts = self.get_format_initialization_metadata_parts(
            audio_format_id=audio_format_id,
            video_format_id=video_format_id,
            vpabr=vpabr,
        )
        next_header_id = 0
        if audio_format_id is not None:
            audio_segment_parts, next_header_id = self.get_media_segments(
                buffered_segments=self.buffered_segments(vpabr, DEFAULT_NUM_AUDIO_SEGMENTS, audio_format_id),
                total_segments=DEFAULT_NUM_AUDIO_SEGMENTS,
                max_segments=2,
                player_time_ms=vpabr.client_abr_state.player_time_ms,
                start_header_id=next_header_id,
                format_id=audio_format_id,
            )
            parts.extend(audio_segment_parts)

        if video_format_id is not None:
            video_segment_parts, next_header_id = self.get_media_segments(
                buffered_segments=self.buffered_segments(vpabr, DEFAULT_NUM_VIDEO_SEGMENTS, video_format_id),
                total_segments=DEFAULT_NUM_VIDEO_SEGMENTS,
                max_segments=2,
                player_time_ms=vpabr.client_abr_state.player_time_ms,
                start_header_id=next_header_id,
                format_id=video_format_id,
            )
            parts.extend(video_segment_parts)

        return parts


class SabrRedirectAVProfile(BasicAudioVideoProfile):

    DEFAULT_REDIRECTS = {
        # 1. Redirect with data on 2nd request
        2: {'url': 'https://redirect.example.com/sabr', 'replace': False},
        # 2. Redirect with no other data after that
        3: {'url': 'https://redirect.example.com/final', 'replace': True},
    }

    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[UMPPart]:
        redirects = self.options.get('redirects', self.DEFAULT_REDIRECTS)
        parts = super().get_parts(vpabr, url, request_number)

        # Guard to ensure the redirect is followed correctly.
        # Get the last redirect_url based on the rn.
        expected_url = None
        for redirect_rn in sorted(redirects.keys(), reverse=True):
            if request_number > redirect_rn:
                expected_url = redirects[redirect_rn]['url']
                break
        if expected_url and not url.startswith(expected_url):
            raise Exception(f'Unexpected URL {url} for request number {request_number}, expected to start with {expected_url}')

        # Handle redirects based on request number
        redirect = redirects.get(request_number)
        if redirect:
            data = protobug.dumps(SabrRedirect(redirect_url=redirect['url']))
            part = UMPPart(
                part_id=UMPPartId.SABR_REDIRECT,
                size=len(data),
                data=io.BytesIO(data),
            )
            if redirect['replace']:
                parts = [part]
            else:
                parts.append(part)
        return parts


class RequestRetryAVProfile(BasicAudioVideoProfile):
    """Test helper profile that injects an error on a particular request number (default 2).

    Used to simulate *request* errors to test retry logic.

    Options:
    mode: 'transport' | 'http' | 'request'
    status: int | None (default None) - HTTP status code to use for 'http' mode
    rn: list of request numbers to inject errors on (default [2])
    """

    def process_request(self, data: bytes, url: str, request_number: int) -> tuple[VideoPlaybackAbrRequest | None, list[UMPPart], int]:
        mode = self.options.get('mode', 'transport')
        status = self.options.get('status')
        if request_number in self.options.get('rn', [2]):
            if mode == 'transport':
                raise TransportError(cause='simulated transport error')
            elif mode == 'http':
                resp = Response(fp=io.BytesIO(b''), url=url, headers={}, status=status or 500)
                raise HTTPError(response=resp)
            elif mode == 'request':
                raise RequestError(msg='simulated request error')
        return super().process_request(data, url, request_number)


class AdWaitAVProfile(BasicAudioVideoProfile):

    # Note: GVS Server requires client to wait the specified time before continuing
    # For test purposes we can assert this happens on the client side.

    CONTEXT_UPDATE_DATA = b'context-update-data'
    CONTEXT_UPDATE_TYPE = 5
    CONTEXT_UPDATE_SCOPE = SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_CONTENT_ADS
    AD_WAIT_TIME = 10

    # Returns a SabrContextUpdate and required the context update to be passed in the vpabr before continuing
    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[UMPPart | Exception]:
        if vpabr.streamer_context.sabr_contexts and any(
            context.type == self.CONTEXT_UPDATE_TYPE
            and context.value == self.CONTEXT_UPDATE_DATA
            for context in vpabr.streamer_context.sabr_contexts
        ):
            # Context update provided, continue with normal processing
            return super().get_parts(vpabr, url, request_number)
        else:
            # Context update not provided yet, return the wait part
            return self.generate_ad_wait_parts()

    def generate_ad_wait_parts(self) -> list[UMPPart]:
        parts = []
        context_update = protobug.dumps(SabrContextUpdate(
            type=self.CONTEXT_UPDATE_TYPE,
            scope=self.CONTEXT_UPDATE_SCOPE,
            value=self.CONTEXT_UPDATE_DATA,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
            send_by_default=True,
        ))
        parts.append(UMPPart(
            part_id=UMPPartId.SABR_CONTEXT_UPDATE,
            size=len(context_update),
            data=io.BytesIO(context_update),
        ))

        # NextRequestPolicy part to indicate wait time
        next_request_policy_data = protobug.dumps(NextRequestPolicy(
            backoff_time_ms=self.AD_WAIT_TIME,
        ))
        parts.append(UMPPart(
            part_id=UMPPartId.NEXT_REQUEST_POLICY,
            size=len(next_request_policy_data),
            data=io.BytesIO(next_request_policy_data),
        ))
        return parts


class SabrContextSendingPolicyAVProfile(BasicAudioVideoProfile):
    # Returns a SabrContextUpdate part on the first request, then a followup policy to disable it
    CONTEXT_UPDATE_DATA = b'context-update-data'
    CONTEXT_UPDATE_TYPE = 1
    CONTEXT_UPDATE_SCOPE = SabrContextUpdate.SabrContextScope.SABR_CONTEXT_SCOPE_PLAYBACK

    REQUEST_ADD_CONTEXT_UPDATE = 1
    REQUEST_DISABLE_CONTEXT_UPDATE = 3

    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[UMPPart | Exception]:
        parts = []
        if request_number == self.REQUEST_ADD_CONTEXT_UPDATE:
            parts.append(self.create_context_update())
        elif request_number == self.REQUEST_DISABLE_CONTEXT_UPDATE:
            parts.append(self.create_disable_context())
        parts.extend(super().get_parts(vpabr, url, request_number))
        return parts

    def create_context_update(self):
        context_update = protobug.dumps(SabrContextUpdate(
            type=self.CONTEXT_UPDATE_TYPE,
            scope=self.CONTEXT_UPDATE_SCOPE,
            value=self.CONTEXT_UPDATE_DATA,
            write_policy=SabrContextUpdate.SabrContextWritePolicy.SABR_CONTEXT_WRITE_POLICY_OVERWRITE,
            send_by_default=True,
        ))
        return UMPPart(
            part_id=UMPPartId.SABR_CONTEXT_UPDATE,
            size=len(context_update),
            data=io.BytesIO(context_update),
        )

    def create_disable_context(self):
        sending_policy = protobug.dumps(SabrContextSendingPolicy(
            stop_policy=[self.CONTEXT_UPDATE_TYPE]))
        return UMPPart(
            part_id=UMPPartId.SABR_CONTEXT_SENDING_POLICY,
            size=len(sending_policy),
            data=io.BytesIO(sending_policy),
        )


class CustomAVProfile(BasicAudioVideoProfile):
    # Allow a test to modify the parts returned via a function
    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[UMPPart | Exception]:
        parts = super().get_parts(vpabr, url, request_number)
        custom_parts_function = self.options.get('custom_parts_function')
        if custom_parts_function:
            parts = custom_parts_function(parts, vpabr, url, request_number)
        return parts


class PoTokenAVProfile(BasicAudioVideoProfile):
    """
    Require a PO token to be present in the vpabr.streamer_context.po_token.
    If not present, return a StreamProtectionStatus part indicating attestation is required.
    If the po_token is 'pending', returns a StreamProtectionStatus part indicating attestation is pending.
    Otherwise, indicate OK.
    """

    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[UMPPart | Exception]:
        parts = []
        if vpabr.streamer_context.po_token is None:
            status = StreamProtectionStatus.Status.ATTESTATION_REQUIRED
        elif vpabr.streamer_context.po_token == b'pending':
            status = StreamProtectionStatus.Status.ATTESTATION_PENDING
        else:
            status = StreamProtectionStatus.Status.OK

        # xxx: max_retries should be ignored by SabrStream
        stream_protection_status_data = protobug.dumps(StreamProtectionStatus(status=status, max_retries=1))
        parts.append(UMPPart(
            part_id=UMPPartId.STREAM_PROTECTION_STATUS,
            size=len(stream_protection_status_data),
            data=io.BytesIO(stream_protection_status_data),
        ))
        if status == StreamProtectionStatus.Status.ATTESTATION_REQUIRED:
            return parts
        parts.extend(super().get_parts(vpabr, url, request_number))
        return parts


def assert_media_sequence_in_order(parts, format_selector: AudioSelector | VideoSelector, expected_total_segments: int, allow_retry=False):
    # Checks that for the given format_selector, the media segments are in order:
    # MediaSegmentInitSabrPart -> MediaSegmentDataSabrPart* -> MediaSegmentEndSabrPart

    total_segments = 0
    current_segment = [None, [], None]

    total_retried_segments = 0

    for part in parts:
        if isinstance(part, MediaSegmentInitSabrPart):
            if part.format_selector == format_selector:
                if current_segment[0] is not None:
                    if not allow_retry:
                        assert current_segment[2] is not None, 'Previous Media segment end part missing'
                    if current_segment[0].sequence_number is None:
                        assert part.sequence_number == 1, 'Segment after init part should be sequence number 1'
                    elif not allow_retry:
                        assert part.sequence_number == current_segment[0].sequence_number + 1, 'Media segment init part sequence number out of order'
                    else:
                        # Allowed to be current or next sequence number
                        if part.sequence_number == current_segment[0].sequence_number:
                            total_retried_segments += 1
                        assert part.sequence_number in (current_segment[0].sequence_number, current_segment[0].sequence_number + 1), 'Media segment init part sequence number out of order'
                current_segment = [part, [], None]
                total_segments += 1
        elif isinstance(part, MediaSegmentDataSabrPart):
            if part.format_selector == format_selector:
                assert current_segment[0] is not None, 'Media segment data part without init part'
                assert part.sequence_number == current_segment[0].sequence_number, 'Media segment data part sequence number mismatch'
                current_segment[1].append(part)
        elif isinstance(part, MediaSegmentEndSabrPart):
            if part.format_selector == format_selector:
                assert current_segment[0] is not None, 'Media segment end part without init part'
                assert current_segment[1], 'Media segment end part without data parts'
                assert current_segment[2] is None, 'Multiple Media segment end parts for the same segment'
                assert part.sequence_number == current_segment[0].sequence_number, 'Media segment end part sequence number mismatch'
                current_segment[2] = part

    assert current_segment[0].sequence_number == current_segment[0].total_segments, 'Last media segment sequence number does not match total segments'
    assert total_segments - total_retried_segments == expected_total_segments, f'Expected {expected_total_segments} segments, got {total_segments}'


def create_inject_read_error(request_numbers: list[int], part_id: UMPPartId, occurance=1):
    def inject_read_error(parts, vpabr, url, request_number):
        # Note: This will need to inject the error after the MEDIA part
        if request_number not in request_numbers:
            return parts
        # Inject error after occurance'th matching part
        new_parts = []
        part_injected = False
        count = 0
        for part in parts:
            if part.part_id == part_id:
                count += 1
            if part.part_id == part_id and count == occurance and not part_injected:
                new_parts.append(part)
                new_parts.append(TransportError('simulated read error'))
                part_injected = True
            else:
                new_parts.append(part)
        return new_parts
    return inject_read_error
