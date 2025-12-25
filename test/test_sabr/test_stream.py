from __future__ import annotations
import base64
import dataclasses
import io
import time
from unittest.mock import MagicMock
import protobug
import pytest
from yt_dlp import int_or_none
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import SabrStreamError
from yt_dlp.networking.exceptions import TransportError, HTTPError, RequestError

from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    FormatInitializedSabrPart,
    MediaSegmentInitSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
    RefreshPlayerResponseSabrPart,
)
from yt_dlp.extractor.youtube._streaming.sabr.stream import SabrStream
from yt_dlp.networking import Request, Response
from yt_dlp.extractor.youtube._proto.videostreaming import (
    VideoPlaybackAbrRequest,
    SabrError,
    FormatId,
    FormatInitializationMetadata,
    MediaHeader,
    BufferedRange,
    TimeRange,
    SabrRedirect,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPEncoder, UMPPart, UMPPartId, write_varint
from yt_dlp.utils import parse_qs

RAW_VIDEO_PLAYBACK_USTREAMER_CONFIG = b'test-config'
VIDEO_PLAYBACK_USTREAMER_CONFIG = base64.urlsafe_b64encode(RAW_VIDEO_PLAYBACK_USTREAMER_CONFIG).decode('utf-8')
VIDEO_ID = 'test_video_id'

DEFAULT_NUM_AUDIO_SEGMENTS = 5
DEFAULT_NUM_VIDEO_SEGMENTS = 10
DEFAULT_MEDIA_SEGMENT_DATA = b'example-media-segment'
DEFAULT_DURATION_MS = 10000
DEFAULT_INIT_SEGMENT_DATA = b'example-init-segment'


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

        fp = io.BytesIO()
        with UMPEncoder(fp) as encoder:
            for part in parts:
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
            vpabr=vpabr,
        ))

        return response


class SabrResponseProcessor:

    def __init__(self, options: dict | None = None):
        self.options = options or {}

    def process_request(self, data: bytes, url: str, request_number: int) -> tuple[VideoPlaybackAbrRequest | None, list[UMPPart], int]:
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
        # TODO: caption format ids, consider initialized_format_ids, enabled_track_types_bitfield
        audio_format_ids = vpabr.selected_audio_format_ids
        video_format_ids = vpabr.selected_video_format_ids

        audio_format_id = audio_format_ids[0] if audio_format_ids else FormatId(itag=140, lmt=123)
        video_format_id = video_format_ids[0] if video_format_ids else FormatId(itag=248, lmt=456)
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
        fim_parts = self.get_format_initialization_metadata_parts(
            audio_format_id=audio_format_id,
            video_format_id=video_format_id,
            vpabr=vpabr,
        )

        audio_segment_parts, next_header_id = self.get_media_segments(
            buffered_segments=self.buffered_segments(vpabr, DEFAULT_NUM_AUDIO_SEGMENTS, audio_format_id),
            total_segments=DEFAULT_NUM_AUDIO_SEGMENTS,
            max_segments=2,
            player_time_ms=vpabr.client_abr_state.player_time_ms,
            start_header_id=0,
            format_id=audio_format_id,
        )
        video_segment_parts, next_header_id = self.get_media_segments(
            buffered_segments=self.buffered_segments(vpabr, DEFAULT_NUM_VIDEO_SEGMENTS, video_format_id),
            total_segments=DEFAULT_NUM_VIDEO_SEGMENTS,
            max_segments=2,
            player_time_ms=vpabr.client_abr_state.player_time_ms,
            start_header_id=next_header_id,
            format_id=video_format_id,
        )
        return [
            *fim_parts,
            *audio_segment_parts,
            *video_segment_parts,
        ]


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


def assert_media_sequence_in_order(parts, format_selector: AudioSelector | VideoSelector, expected_total_segments: int):
    # Checks that for the given format_selector, the media segments are in order:
    # MediaSegmentInitSabrPart -> MediaSegmentDataSabrPart* -> MediaSegmentEndSabrPart

    total_segments = 0
    current_segment = [None, [], None]

    for part in parts:
        if isinstance(part, MediaSegmentInitSabrPart):
            if part.format_selector == format_selector:
                if current_segment[0] is not None:
                    assert current_segment[2] is not None
                    if current_segment[0].sequence_number is None:
                        assert part.sequence_number == 1
                    else:
                        assert part.sequence_number == current_segment[0].sequence_number + 1
                current_segment = [part, [], None]
                total_segments += 1
        elif isinstance(part, MediaSegmentDataSabrPart):
            if part.format_selector == format_selector:
                assert current_segment[0] is not None
                assert part.sequence_number == current_segment[0].sequence_number
                current_segment[1].append(part)
        elif isinstance(part, MediaSegmentEndSabrPart):
            if part.format_selector == format_selector:
                assert current_segment[0] is not None
                assert current_segment[1]
                assert current_segment[2] is None
                assert part.sequence_number == current_segment[0].sequence_number
                current_segment[2] = part

    assert current_segment[0].sequence_number == current_segment[0].total_segments == expected_total_segments == (total_segments - 1)


def setup_sabr_stream_av(
    url='https://example.com/sabr',
    sabr_response_processor=None,
    client_info=None,
    logger=None,
    **options,
):
    rh = SabrRequestHandler(sabr_response_processor=sabr_response_processor or BasicAudioVideoProfile())
    audio_selector = AudioSelector(display_name='audio')
    video_selector = VideoSelector(display_name='video')
    sabr_stream = SabrStream(
        urlopen=rh.send,
        server_abr_streaming_url=url,
        logger=logger,
        video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
        client_info=client_info,
        audio_selection=audio_selector,
        video_selection=video_selector,
        **options,
    )
    return sabr_stream, rh, (audio_selector, video_selector)


class TestStream:
    def test_sabr_audio_video(self, logger, client_info):
        # Basic successful case that both audio and video formats are requested and returned.
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )

        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        # 1. Check we got two format initialization metadata parts for the two formats.
        format_init_parts = [part for part in parts if isinstance(part, FormatInitializedSabrPart)]
        assert len(format_init_parts) == 2
        assert format_init_parts[0].format_id == FormatId(itag=140, lmt=123)
        assert format_init_parts[0].format_selector == audio_selector
        assert format_init_parts[1].format_id == FormatId(itag=248, lmt=456)
        assert format_init_parts[1].format_selector == video_selector

        # 2. Check that media segments are in order for both audio and video selectors.
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

        assert len(rh.request_history) == 6

    def test_sabr_basic_buffers(self, logger, client_info):
        # Check that basic audio and video buffering works as expected
        # with player time updates based on the shorter of the two streams.
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )

        list(sabr_stream.iter_parts())
        assert len(rh.request_history) == 6

        # First empty request
        assert rh.request_history[0].vpabr.buffered_ranges == []
        # Player time is at 0
        assert rh.request_history[0].vpabr.client_abr_state.player_time_ms == 0

        # Second request, first segment buffered
        assert rh.request_history[1].vpabr.buffered_ranges == [
            BufferedRange(
                format_id=FormatId(itag=140, lmt=123, xtags=None),
                start_time_ms=0, duration_ms=2000, start_segment_index=1, end_segment_index=1,
                time_range=TimeRange(start_ticks=0, duration_ticks=2000, timescale=1000)),
            BufferedRange(
                format_id=FormatId(itag=248, lmt=456, xtags=None),
                start_time_ms=0, duration_ms=1000, start_segment_index=1, end_segment_index=1,
                time_range=TimeRange(start_ticks=0, duration_ticks=1000, timescale=1000))]
        # Player time should now be at 1000ms - based on audio segment (shorter of the two)
        assert rh.request_history[1].vpabr.client_abr_state.player_time_ms == 1000

        # Second request, first segment buffered
        assert rh.request_history[2].vpabr.buffered_ranges == [
            BufferedRange(
                format_id=FormatId(itag=140, lmt=123, xtags=None),
                start_time_ms=0, duration_ms=6001, start_segment_index=1, end_segment_index=3,
                time_range=TimeRange(start_ticks=0, duration_ticks=6001, timescale=1000)),
            BufferedRange(
                format_id=FormatId(itag=248, lmt=456, xtags=None),
                start_time_ms=0, duration_ms=3001, start_segment_index=1, end_segment_index=3,
                time_range=TimeRange(start_ticks=0, duration_ticks=3001, timescale=1000))]

        assert rh.request_history[2].vpabr.client_abr_state.player_time_ms == 3001
        assert rh.request_history[3].vpabr.client_abr_state.player_time_ms == 5001
        assert rh.request_history[4].vpabr.client_abr_state.player_time_ms == 7001

        # Final request should have all but last segments buffered
        assert rh.request_history[5].vpabr.buffered_ranges == [
            BufferedRange(
                format_id=FormatId(itag=140, lmt=123, xtags=None),
                start_time_ms=0, duration_ms=10001, start_segment_index=1, end_segment_index=5,
                time_range=TimeRange(start_ticks=0, duration_ticks=10001, timescale=1000)),
            BufferedRange(
                format_id=FormatId(itag=248, lmt=456, xtags=None),
                start_time_ms=0, duration_ms=9001, start_segment_index=1, end_segment_index=9,
                time_range=TimeRange(start_ticks=0, duration_ticks=9001, timescale=1000))]
        assert rh.request_history[5].vpabr.client_abr_state.player_time_ms == 9001

    def test_sabr_request_number(self, logger, client_info):
        # Should set the "rn" query parameter correctly on each request
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        list(sabr_stream.iter_parts())
        assert len(rh.request_history) == 6
        for idx, request_details in enumerate(rh.request_history):
            expected_rn = str(idx + 1)
            actual_rn = parse_qs(request_details.request.url).get('rn', [None])[0]
            assert actual_rn == expected_rn, f'Expected rn={expected_rn}, got rn={actual_rn}'

    def test_sabr_request_headers(self, logger, client_info):
        # Should set the correct headers on each request
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        list(sabr_stream.iter_parts())
        assert len(rh.request_history) == 6
        for request_details in rh.request_history:
            request = request_details.request
            assert request.headers.get('content-type') == 'application/x-protobuf'
            assert request.headers.get('accept-encoding') == 'identity'
            assert request.headers.get('accept') == 'application/vnd.yt-ump'

    def test_sabr_basic_redirect(self, logger, client_info):
        # Test successful redirect handling
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=SabrRedirectAVProfile(),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors

        assert sabr_stream.url == 'https://example.com/sabr'
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

        assert len(rh.request_history) == 7
        assert rh.request_history[0].request.url == 'https://example.com/sabr?rn=1'
        assert rh.request_history[2].request.url == 'https://redirect.example.com/sabr?rn=3'
        assert rh.request_history[3].request.url == 'https://redirect.example.com/final?rn=4'
        assert rh.request_history[4].request.url == 'https://redirect.example.com/final?rn=5'
        assert sabr_stream.url == 'https://redirect.example.com/final'

    def test_sabr_reject_http_url(self, logger, client_info):
        # Do not allow HTTP URLs for server_abr_streaming_url
        rh = SabrRequestHandler(sabr_response_processor=BasicAudioVideoProfile())
        audio_selector = AudioSelector(display_name='audio')
        video_selector = VideoSelector(display_name='video')
        with pytest.raises(SabrStreamError, match='Insecure URL scheme http:// is not allowed for SABR streaming URL'):
            SabrStream(
                urlopen=rh.send,
                server_abr_streaming_url='http://example.com/sabr',
                logger=logger,
                video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
                client_info=client_info,
                audio_selection=audio_selector,
                video_selection=video_selector,
            )

    def test_sabr_url_update(self, logger, client_info):
        # Should allow the caller to update the URL mid-stream and use it
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.url == 'https://example.com/sabr'

        # Retrieve 4 requests (based on request_history)
        parts = []
        parts_iter = sabr_stream.iter_parts()
        while len(rh.request_history) < 4:
            parts.append(next(parts_iter))
        # Update the URL
        sabr_stream.url = 'https://new.example.com/sabr'
        assert sabr_stream.url == 'https://new.example.com/sabr'
        # Continue retrieving parts
        parts.extend(list(parts_iter))
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

        assert len(rh.request_history) == 6
        assert rh.request_history[0].request.url == 'https://example.com/sabr?rn=1'
        assert rh.request_history[1].request.url == 'https://example.com/sabr?rn=2'
        assert rh.request_history[2].request.url == 'https://example.com/sabr?rn=3'
        assert rh.request_history[3].request.url == 'https://example.com/sabr?rn=4'
        assert rh.request_history[4].request.url == 'https://new.example.com/sabr?rn=5'
        assert rh.request_history[5].request.url == 'https://new.example.com/sabr?rn=6'
        assert sabr_stream.url == 'https://new.example.com/sabr'

    @pytest.mark.parametrize(
        'bad_url',
        [None, '', 'bad-url%', 'http://insecure.example.com', 'file:///etc/passwd', 'https://example.org/sabr'],
        ids=['none', 'empty', 'malformed', 'insecure', 'file scheme', 'different domain'])
    def test_sabr_update_url_invalid(self, logger, client_info, bad_url):
        # Should reject invalid URLs relative to the current URL when updating sabr_stream.url
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        assert sabr_stream.url == 'https://example.com/sabr'

        with pytest.raises(SabrStreamError, match='Invalid SABR streaming URL'):
            sabr_stream.url = bad_url

        assert sabr_stream.url == 'https://example.com/sabr'

    @pytest.mark.parametrize(
        'bad_url',
        [None, '', 'bad-url%', 'http://insecure.example.com', 'file:///etc/passwd', 'https://example.org/sabr'],
        ids=['none', 'empty', 'malformed', 'insecure', 'file scheme', 'different domain'])
    def test_sabr_process_redirect_invalid_url(self, logger, client_info, bad_url):
        # Should ignore an invalid redirect URl and continue with the current URL
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=SabrRedirectAVProfile({'redirects': {2: {'url': bad_url, 'replace': True}}}),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)
        assert len(rh.request_history) == 7
        assert sabr_stream.url == 'https://example.com/sabr'
        logger.warning.assert_any_call(f'Server requested to redirect to an invalid URL: {bad_url}')

    def test_sabr_set_live_from_url_source(self, logger, client_info):
        # Should set is_live to True based on source URL parameter
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr?source=yt_live_broadcast',
        )
        assert sabr_stream.url == 'https://example.com/sabr?source=yt_live_broadcast'
        assert sabr_stream.processor.is_live is True

    def test_sabr_nonlive_ignore_broadcast_id_update(self, logger, client_info):
        # Should ignore broadcast_id updates in URL when non-live
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr?id=1',
        )

        assert sabr_stream.processor.is_live is False
        sabr_stream.url = 'https://example.com/sabr?id=2'
        assert sabr_stream.processor.is_live is False
        assert sabr_stream.url == 'https://example.com/sabr?id=2'

    @pytest.mark.parametrize('post_live', [True, False], ids=['post_live=True', 'post_live=False'])
    def test_sabr_live_error_on_broadcast_id_update(self, logger, client_info, post_live):
        # Should raise an error if broadcast_id changes for live stream. Post live flag should not affect this.
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr?source=yt_live_broadcast&id=1',
            post_live=post_live,
        )

        assert sabr_stream.processor.is_live is True
        with pytest.raises(SabrStreamError, match=r'Broadcast ID changed from 1 to 2\. The download will need to be restarted\.'):
            sabr_stream.url = 'https://example.com/sabr?source=yt_live_broadcast&id=2'

    def test_sabr_expiry_refresh_player_response(self, logger, client_info):
        # Should yield a refresh player response part if within the expiry time
        # This should occur before the next request
        expires_at = int(time.time() + 30)  # 30 seconds from now
        sabr_stream, rh, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url=f'https://example.com/sabr?expire={int(expires_at)}',
            # By default, expiry threshold is 60 seconds
        )
        # Retrieve parts until we get a RefreshPlayerResponseSabrPart
        refresh_part = None
        while not refresh_part:
            part = next(sabr_stream.iter_parts())
            if isinstance(part, RefreshPlayerResponseSabrPart):
                refresh_part = part
        # Should be no requests made so far as checking expiry happens before request
        assert len(rh.request_history) == 0
        assert refresh_part is not None
        assert refresh_part.reason == RefreshPlayerResponseSabrPart.Reason.SABR_URL_EXPIRY
        logger.debug.assert_called_with(r'Requesting player response refresh as SABR URL is due to expire within 60 seconds')

    def test_sabr_expiry_threshold_sec(self, logger, client_info):
        # Should use the configured expiry threshold seconds when determining to refresh player response
        expires_at = int(time.time() + 100)  # 100 seconds from now
        sabr_stream, rh, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url=f'https://example.com/sabr?expire={int(expires_at)}',
            expiry_threshold_sec=120,  # Set threshold to 2 minutes
        )

        # Retrieve parts until we get a RefreshPlayerResponseSabrPart
        refresh_part = None
        while not refresh_part:
            part = next(sabr_stream.iter_parts())
            if isinstance(part, RefreshPlayerResponseSabrPart):
                refresh_part = part
        # Should be no requests made so far as checking expiry happens before request
        assert len(rh.request_history) == 0
        assert refresh_part is not None
        assert refresh_part.reason == RefreshPlayerResponseSabrPart.Reason.SABR_URL_EXPIRY
        logger.debug.assert_called_with(r'Requesting player response refresh as SABR URL is due to expire within 120 seconds')

    def test_sabr_no_expiry_in_url(self, logger, client_info):
        # Should not yield a refresh player response part if no expiry in URL
        # It should log a warning about missing expiry
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr',
        )
        parts = list(sabr_stream.iter_parts())
        assert all(not isinstance(part, RefreshPlayerResponseSabrPart) for part in parts)
        logger.warning.assert_called_with('No expiry timestamp found in SABR URL. Will not be able to refresh.', once=True)

    def test_sabr_not_expired(self, logger, client_info):
        # Should not yield a refresh player response part if not within the expiry threshold
        expires_at = int(time.time() + 300)  # 5 minutes from now
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url=f'https://example.com/sabr?expire={int(expires_at)}',
            # By default, expiry threshold is 60 seconds
        )
        parts = list(sabr_stream.iter_parts())
        assert all(not isinstance(part, RefreshPlayerResponseSabrPart) for part in parts)

    class TestRequestRetries:
        def test_sabr_retry_on_transport_error(self, logger, client_info):
            # Should retry on TransportError occurring during request
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

            # Find the first request that recorded an error
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)

            request = rh.request_history[i_err]
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

            # There should be a retry request recorded immediately after the error
            retried_request = rh.request_history[i_err + 1]
            assert retried_request.error is None

            # The video_playback_abr_request should be the same for both requests - no changes in state (e.g playback time)
            assert request.request.data == retried_request.request.data

            # Should log the retry attempt
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')

        def test_sabr_retry_on_http_5xx(self, logger, client_info):
            # Should retry on HTTP 5xx errors
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'http', 'status': 500, 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )

            parts = list(sabr_stream.iter_parts())
            audio_selector, video_selector = selectors
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

            # Find the first request that recorded an error
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)

            request = rh.request_history[i_err]
            assert isinstance(request.error, HTTPError)
            assert request.error.status == 500

            # There should be a retry request recorded immediately after the error
            retried_request = rh.request_history[i_err + 1]
            assert retried_request.error is None
            # The video_playback_abr_request should be the same for both requests - no changes in state (e.g playback time)
            assert request.request.data == retried_request.request.data
            # Should log the retry attempt
            logger.warning.assert_any_call('[sabr] Got error: HTTP Error 500: Internal Server Error. Retrying (1/10)...')

        def test_sabr_no_retry_on_http_4xx(self, logger, client_info):
            # Should NOT retry on HTTP 4xx errors and should raise SabrStreamError
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'http', 'status': 404, 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )

            with pytest.raises(SabrStreamError, match=r'404'):
                list(sabr_stream.iter_parts())

            # Ensure the failing request was recorded and no retry was attempted
            assert len(rh.request_history) >= 1
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)
            assert isinstance(rh.request_history[i_err].error, HTTPError)
            assert rh.request_history[i_err].error.status == 404
            assert len(rh.request_history) == i_err + 1

        def test_sabr_no_retry_on_request_error(self, logger, client_info):
            # Should NOT retry on RequestError (non-network error)
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'request', 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )
            # We don't currently wrap in SabrStreamError as could be client issue
            with pytest.raises(RequestError, match='simulated request error'):
                list(sabr_stream.iter_parts())

            # Ensure the failing request was recorded and no retry was attempted
            assert len(rh.request_history) >= 1
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)
            assert isinstance(rh.request_history[i_err].error, RequestError)
            assert len(rh.request_history) == i_err + 1

        def test_sabr_multiple_retries(self, logger, client_info):
            # Should retry multiple times on consecutive errors
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 3, 4]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

            # Find the requests that recorded errors
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 3
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # There should be a retry request recorded immediately after the three errors
            last_error_request = error_requests[-1]
            retried_request = rh.request_history[rh.request_history.index(last_error_request) + 1]
            assert retried_request.error is None
            # The video_playback_abr_request should be the same for all requests - no changes in state (e.g playback time)
            assert error_requests[0].request.data == retried_request.request.data

            # Should log each retry attempt
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (2/10)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (3/10)...')

        def test_sabr_reset_retry_counter(self, logger, client_info):
            # Should reset the retry counter after a successful request
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 4]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS)

            # Find the requests that recorded errors
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 2
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # There should be a retry request recorded immediately after each error
            first_error_request = error_requests[0]
            first_retried_request = rh.request_history[rh.request_history.index(first_error_request) + 1]
            assert first_retried_request.error is None
            second_error_request = error_requests[1]
            second_retried_request = rh.request_history[rh.request_history.index(second_error_request) + 1]
            assert second_retried_request.error is None

            # Should log each retry attempt with correct counts
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')

        def test_sabr_exceed_max_retries(self, logger, client_info):
            # Should raise SabrStreamError after exceeding max retries
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
                client_info=client_info,
                logger=logger,
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be max_retry + 1 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 11  # Default max retries is 10
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Should log each retry attempt
            for i in range(1, 11):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        def test_sabr_http_retries_option(self, logger, client_info):
            # Should respect the http_retries option for max retries
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 8))}),
                client_info=client_info,
                logger=logger,
                http_retries=5,
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be http_retries + 1 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 6  # http_retries is set to 5
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Should log each retry attempt
            for i in range(1, 6):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/5)...')

        def test_sabr_http_retry_sleep_func(self, logger, client_info):
            # Should call the retry_sleep_func between retries to get the sleep duration
            # For this test, we want to return 0.001 as the sleep
            sleep_mock = MagicMock()
            sleep_mock.side_effect = lambda n: 0.001

            sabr_stream, _, __ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 3]}),
                client_info=client_info,
                logger=logger,
                http_retries=3,
                retry_sleep_func=sleep_mock,
            )
            # Should complete successfully
            list(sabr_stream.iter_parts())
            # sleep_mock should be called 2 times (for the two retries)
            assert sleep_mock.call_count == 2
            sleep_mock.assert_any_call(n=0)
            sleep_mock.assert_any_call(n=1)

            # Check logs for retry attempts
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/3)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (2/3)...')
            # Should log the sleep
            logger.info.assert_any_call('Sleeping 0.00 seconds ...')

        def test_sabr_expiry_on_retry(self, logger, client_info):
            # Should check for expiry before retrying and yield RefreshPlayerResponseSabrPart if within threshold
            expires_at = int(time.time() + 30)  # 30 seconds from now
            sabr_stream, _, __ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(7))}),
                client_info=client_info,
                logger=logger,
                url=f'https://example.com/sabr?expire={int(expires_at)}',
                http_retries=5,
                # By default, expiry threshold is 60 seconds
            )

            # Retrieve all parts until we fail
            parts = []
            with pytest.raises(TransportError, match='simulated transport error'):
                for part in sabr_stream.iter_parts():
                    parts.append(part)

            # Should get 6 RefreshPlayerResponseSabrPart parts before failing
            # (If the check was AFTER the retry was triggered, we would only get 1)
            refresh_parts = [part for part in parts if isinstance(part, RefreshPlayerResponseSabrPart)]
            assert len(refresh_parts) == 6

        def test_sabr_increment_rn_on_retry(self, logger, client_info):
            # Should increment the "rn" parameter on each retry request
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 3, 4]}),
                client_info=client_info,
                logger=logger,
            )

            # Should complete successfully
            list(sabr_stream.iter_parts())

            # Find the requests that recorded errors
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 3

            # Check that the "rn" parameter increments correctly
            for i, request_details in enumerate(rh.request_history):
                expected_rn = i + 1
                actual_rn = extract_rn(request_details.request.url)
                assert actual_rn == expected_rn, f'Expected rn={expected_rn}, got rn={actual_rn}'
