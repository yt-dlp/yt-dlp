from __future__ import annotations
import base64
import dataclasses
import io
import protobug
from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector
from yt_dlp.extractor.youtube._streaming.sabr.stream import SabrStream
from yt_dlp.networking import Request, Response
from yt_dlp.extractor.youtube._proto.videostreaming import (
    VideoPlaybackAbrRequest,
    SabrError,
    FormatId,
    FormatInitializationMetadata,
    MediaHeader,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPEncoder, UMPPart, UMPPartId, write_varint

VIDEO_PLAYBACK_USTREAMER_CONFIG = base64.urlsafe_b64encode(b'test-config').decode('utf-8')
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


class TestStream:
    def test_sabr_request_handler(self, logger, client_info):

        rh = SabrRequestHandler(sabr_response_processor=BasicAudioVideoProfile())

        sabr_stream = SabrStream(
            urlopen=rh.send,
            server_abr_streaming_url='https://example.com/sabr',
            logger=logger,
            video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
            client_info=client_info,
            audio_selection=AudioSelector(display_name='audio'),
            video_selection=VideoSelector(display_name='video'),
        )

        for part in sabr_stream.iter_parts():
            print(part)
        print(logger.mock_calls)
