from __future__ import annotations
import base64
import dataclasses
import io
import protobug
import pytest

from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    FormatInitializedSabrPart,
    MediaSegmentInitSabrPart,
    MediaSegmentDataSabrPart,
    MediaSegmentEndSabrPart,
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

RAW_VIDEO_PLAYBACK_USTREAMER_CONFIG = b'test-config'
VIDEO_PLAYBACK_USTREAMER_CONFIG = base64.urlsafe_b64encode(RAW_VIDEO_PLAYBACK_USTREAMER_CONFIG).decode('utf-8')
VIDEO_ID = 'test_video_id'

DEFAULT_NUM_AUDIO_SEGMENTS = 5
DEFAULT_NUM_VIDEO_SEGMENTS = 10
DEFAULT_MEDIA_SEGMENT_DATA = b'example-media-segment'
DEFAULT_DURATION_MS = 10000
DEFAULT_INIT_SEGMENT_DATA = b'example-init-segment'


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
            vpabr, parts, response_code = self.sabr_response_processor.process_request(request.data, request.url)
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
    def process_request(self, data: bytes, url: str) -> tuple[VideoPlaybackAbrRequest | None, list[UMPPart], int]:
        try:
            vpabr = protobug.loads(data, VideoPlaybackAbrRequest)
        except Exception:
            error_part = protobug.dumps(SabrError(type='sabr.malformed_request'))
            # TODO: confirm GVS behaviour when VideoPlaybackAbrRequest is malformed
            return None, [UMPPart(data=io.BytesIO(error_part), part_id=UMPPartId.SABR_ERROR, size=len(error_part))], 200

        return vpabr, self.get_parts(vpabr, url), 200

    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str) -> list[UMPPart]:
        raise NotImplementedError

    def determine_formats(self, vpabr: VideoPlaybackAbrRequest) -> tuple[FormatId, FormatId]:
        # Check selected_audio_format_ids and selected_video_format_ids
        # TODO: caption format ids, consider initialized_format_ids, enabled_track_types_bitfield
        audio_format_ids = vpabr.selected_audio_format_ids
        video_format_ids = vpabr.selected_video_format_ids

        audio_format_id = audio_format_ids[0] if audio_format_ids else FormatId(itag=140, lmt=123)
        video_format_id = video_format_ids[0] if video_format_ids else FormatId(itag=248, lmt=456)
        return audio_format_id, video_format_id

    def get_format_initialization_metadata_parts(self,
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
    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str) -> list[UMPPart]:
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
    def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str) -> list[UMPPart]:
        parts = super().get_parts(vpabr, url)

        # 1. Redirect with data on 2nd request
        if 'rn=2' in url:
            data = protobug.dumps(SabrRedirect(redirect_url='https://redirect.example.com/sabr'))
            parts.append(UMPPart(
                part_id=UMPPartId.SABR_REDIRECT,
                size=len(data),
                data=io.BytesIO(data),
            ))

        # 2. Redirect with no other data after that
        if url.startswith('https://redirect.example.com/sabr'):
            data = protobug.dumps(SabrRedirect(redirect_url='https://redirect.example.com/final'))
            parts = [UMPPart(
                part_id=UMPPartId.SABR_REDIRECT,
                size=len(data),
                data=io.BytesIO(data),
            )]

        return parts


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


class TestStream:
    def test_sabr_audio_video(self, logger, client_info):
        # Basic successful case that both audio and video formats are requested and returned.
        rh = SabrRequestHandler(sabr_response_processor=BasicAudioVideoProfile())
        audio_selector = AudioSelector(display_name='audio')
        video_selector = VideoSelector(display_name='video')
        sabr_stream = SabrStream(
            urlopen=rh.send,
            server_abr_streaming_url='https://example.com/sabr',
            logger=logger,
            video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
            client_info=client_info,
            audio_selection=audio_selector,
            video_selection=video_selector,
        )

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
        rh = SabrRequestHandler(sabr_response_processor=BasicAudioVideoProfile())
        audio_selector = AudioSelector(display_name='audio')
        video_selector = VideoSelector(display_name='video')
        sabr_stream = SabrStream(
            urlopen=rh.send,
            server_abr_streaming_url='https://example.com/sabr',
            logger=logger,
            video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
            client_info=client_info,
            audio_selection=audio_selector,
            video_selection=video_selector,
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

    def test_sabr_basic_redirect(self, logger, client_info):
        # Test successful redirect handling
        rh = SabrRequestHandler(sabr_response_processor=SabrRedirectAVProfile())
        audio_selector = AudioSelector(display_name='audio')
        video_selector = VideoSelector(display_name='video')
        sabr_stream = SabrStream(
            urlopen=rh.send,
            server_abr_streaming_url='https://example.com/sabr',
            logger=logger,
            video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
            client_info=client_info,
            audio_selection=audio_selector,
            video_selection=video_selector,
        )

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

    @pytest.mark.parametrize('bad_url', [None, '', 'bad-url%', 'http://insecure.example.com', 'file:///etc/passwd', 'https://example.org/sabr'])
    def test_sabr_process_redirect_invalid_url(self, logger, client_info, bad_url):
        # Should ignore an invalid redirect URl and continue with the current URL
        rh = SabrRequestHandler(sabr_response_processor=SabrRedirectAVProfile())
        audio_selector = AudioSelector(display_name='audio')
        video_selector = VideoSelector(display_name='video')
        sabr_stream = SabrStream(
            urlopen=rh.send,
            server_abr_streaming_url='https://example.com/sabr',
            logger=logger,
            video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
            client_info=client_info,
            audio_selection=audio_selector,
            video_selection=video_selector,
        )
        data = protobug.dumps(SabrRedirect(redirect_url=bad_url))
        sabr_stream._process_sabr_redirect(
            UMPPart(part_id=UMPPartId.SABR_REDIRECT, size=len(data), data=io.BytesIO(data)))
        assert sabr_stream.url == 'https://example.com/sabr'
        logger.warning.assert_called_with(f'Server requested to redirect to an invalid URL: {bad_url}')
