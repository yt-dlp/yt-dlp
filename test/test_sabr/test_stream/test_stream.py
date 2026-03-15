from __future__ import annotations
import io
import protobug
import pytest

from test.test_sabr.test_stream.helpers import (
    VIDEO_PLAYBACK_USTREAMER_CONFIG,
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    SabrRequestHandler,
    BasicAudioVideoProfile,
    SabrRedirectAVProfile,
    CustomAVProfile,
    assert_media_sequence_in_order,
    SkipSegmentProfile,
    DEFAULT_AUDIO_FORMAT,
    VALID_SABR_URL,
    setup_sabr_stream_av,
    DEFAULT_VIDEO_FORMAT,
)
from yt_dlp.extractor.youtube._proto.videostreaming.reload_player_response import ReloadPlaybackParams
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import (
    SabrStreamError,
    SabrStreamConsumedError,
    MediaSegmentMismatchError,
    UnexpectedConsumedMediaSegment,
    BroadcastIdChanged,
    InvalidSabrUrl,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart
from yt_dlp.networking.exceptions import TransportError

from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector, ConsumedRange
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    FormatInitializedSabrPart,
    RefreshPlayerResponseSabrPart,
    MediaSegmentInitSabrPart,
)
from yt_dlp.extractor.youtube._streaming.sabr.stream import SabrStream
from yt_dlp.extractor.youtube._proto.videostreaming import (
    FormatId,
    BufferedRange,
    TimeRange,
    ReloadPlayerResponse,
    SabrRedirect,
    VideoPlaybackAbrRequest,
)
from yt_dlp.utils import parse_qs


class TestStream:
    def test_audio_video(self, logger, client_info):
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
        # note: +1 due to init segment
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 6

        # Should have completed due to all segments being retrieved
        logger.trace.assert_any_call(
            'All enabled formats have reached their last expected segment at player time 10001 ms, assuming end of vod.')

    def test_audio_only(self, logger, client_info):
        # Basic successful case that only audio format is requested and returned.
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_video=False,
        )
        audio_selector, _ = selectors
        parts = list(sabr_stream.iter_parts())

        format_init_parts = [part for part in parts if isinstance(part, FormatInitializedSabrPart)]
        assert len(format_init_parts) == 1
        assert format_init_parts[0].format_id == FormatId(itag=140, lmt=123)
        assert format_init_parts[0].format_selector == audio_selector

        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)

        # Ensure we did not get any video segments
        video_parts = [part for part in parts if hasattr(part, 'format_selector') and isinstance(part.format_selector, VideoSelector)]
        assert not video_parts

        assert rh.request_history[0].vpabr.client_abr_state.enabled_track_types_bitfield == 1
        assert len(rh.request_history[1].vpabr.buffered_ranges) == 1

        # Should have completed due to all segments being retrieved
        logger.trace.assert_any_call(
            'All enabled formats have reached their last expected segment at player time 10001 ms, assuming end of vod.')

    def test_video_only(self, logger, client_info):
        # Basic successful case that only video format is requested and returned.
        # NOTE: SABR does not support native video-only, so the client
        # should mark the audio format as completely buffered after the first request.
        # Any audio segments retrieved should be marked as discarded and not returned to the caller.
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )
        _, video_selector = selectors
        parts = list(sabr_stream.iter_parts())

        format_init_parts = [part for part in parts if isinstance(part, FormatInitializedSabrPart)]
        assert len(format_init_parts) == 1
        assert format_init_parts[0].format_id == FormatId(itag=248, lmt=456)
        assert format_init_parts[0].format_selector == video_selector

        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        # Ensure we did not get any audio segments
        audio_parts = [part for part in parts if hasattr(part, 'format_selector') and isinstance(part.format_selector, AudioSelector)]
        assert not audio_parts

        assert rh.request_history[0].vpabr.client_abr_state.enabled_track_types_bitfield == 0

        # Audio format should be marked as completely buffered after first request
        audio_buffered_range = BufferedRange(
            format_id=FormatId(itag=140, lmt=123, xtags=None),
            start_time_ms=0,
            duration_ms=9007199254740991,
            start_segment_index=0,
            end_segment_index=9007199254740991,
            time_range=TimeRange(start_ticks=0, duration_ticks=9007199254740991, timescale=1000))

        assert audio_buffered_range in rh.request_history[1].vpabr.buffered_ranges

        # Should have completed due to all segments being retrieved
        logger.trace.assert_any_call(
            'All enabled formats have reached their last expected segment at player time 10001 ms, assuming end of vod.')

    def test_set_preferred_format_ids(self, logger, client_info):
        # If format_ids are present in the format selector, then the preferred format ids should be set
        sabr_stream, rh, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            enable_video=True,
            enable_audio=True,
            select_with_format_id=True,
        )
        list(sabr_stream.iter_parts())
        assert rh.request_history[0].vpabr.preferred_audio_format_ids == [DEFAULT_AUDIO_FORMAT]
        assert rh.request_history[0].vpabr.preferred_video_format_ids == [DEFAULT_VIDEO_FORMAT]

    def test_audio_video_end_player_time(self, logger, client_info):
        # Should consider stream as finished if player_time_ms is greater than end_time_ms of each format
        # Fallback to when we can't determine end based on segments retrieved
        # Can simulate this by setting start_time_ms to beyond end of stream and not sending any media parts

        def no_media_parts_processor(parts, vpabr, url, request_number):
            return [
                part for part in parts
                if part.part_id not in (UMPPartId.MEDIA_HEADER, UMPPartId.MEDIA, UMPPartId.MEDIA_END)
            ]
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=CustomAVProfile({'custom_parts_function': no_media_parts_processor}),
            client_info=client_info,
            logger=logger,
            start_time_ms=100000,
        )
        parts = list(sabr_stream.iter_parts())
        assert len(parts) == 2  # Only format init parts
        assert all(isinstance(part, FormatInitializedSabrPart) for part in parts)
        assert len(rh.request_history) == 1
        logger.trace.assert_any_call('All enabled formats have reached their end time by player time 100000 ms, assuming end of vod.')

    def test_end_stream_before_discarded_format(self, logger, client_info):
        # If enabled formats are detected as ended before a discarded format,
        # the stream should end without waiting for the discarded format to finish.
        # For this test, we need to clear consumed ranges for the discarded format
        # (to simulate case when we cannot use the consumed ranges trick to ignore format)

        sabr_stream, _, selectors = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )
        _, video_selector = selectors
        # When receive format init part for audio, clear consumed ranges
        iter_parts = sabr_stream.iter_parts()
        parts = []
        for part in iter_parts:
            # keep clearing the discarded audio format consumed ranges once they are set
            audio_izf = sabr_stream.processor.initialized_formats.get(str(DEFAULT_AUDIO_FORMAT))
            if audio_izf:
                assert audio_izf.discard is True
                audio_izf.consumed_ranges = []
            parts.append(part)

        # sanity checking we only get video-only segments
        format_init_parts = [part for part in parts if isinstance(part, FormatInitializedSabrPart)]
        assert len(format_init_parts) == 1
        assert format_init_parts[0].format_id == FormatId(itag=248, lmt=456)
        assert format_init_parts[0].format_selector == video_selector

        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        # Ensure we did not get any audio segments
        audio_parts = [part for part in parts if hasattr(part, 'format_selector') and isinstance(part.format_selector, AudioSelector)]
        assert not audio_parts

        # Should finish stream even though discarded format is not ended
        logger.trace.assert_any_call(
            'All enabled formats have reached their last expected segment at player time 10001 ms, assuming end of vod.')
        assert sabr_stream.processor.initialized_formats[str(DEFAULT_AUDIO_FORMAT)].consumed_ranges == []

    def test_basic_buffers(self, logger, client_info):
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

    def test_multiple_buffered_ranges(self, logger, client_info):
        # Should handle multiple buffered ranges correctly,
        # where if there is another buffered range at the end of a buffered range, it should skip ahead to the end of it.
        # This can happen for live streams and resuming playback.
        # Using video-only to keep this test simple

        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        # Get all the segments from the first iteration. We need to know the timings of each to set up buffered ranges.
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        # Get all the media init parts
        media_init_parts = [part for part in iter_parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts) == DEFAULT_NUM_VIDEO_SEGMENTS + 1

        #  Now set up buffered ranges to skip some segments
        consumed_ranges = [
            # Mark middle segments as buffered (2-9)
            ConsumedRange(
                # Note: First segment is init segment with no sequence number
                start_sequence_number=media_init_parts[2].sequence_number,
                end_sequence_number=media_init_parts[-2].sequence_number,
                start_time_ms=media_init_parts[2].start_time_ms,
                duration_ms=sum(part.duration_ms for part in media_init_parts[2:-1]),
            ),
        ]

        # Reset the sabr stream and set the consumed ranges
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        # Start streaming until get the initialized format
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        sabr_stream.processor.initialized_formats[str(format_init_part.format_id)].consumed_ranges = consumed_ranges
        # Continue retrieving parts
        parts = [format_init_part]
        parts.extend(iter_parts)

        # Expect that the only media init parts we get is init segment, first segment and last segment (10)
        media_init_parts_received = [part for part in parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts_received) == 3
        assert media_init_parts_received[0].sequence_number is None  # init segment
        assert media_init_parts_received[1].sequence_number == 1
        assert media_init_parts_received[2].sequence_number == media_init_parts[-1].sequence_number  # last segment

        # In the last vpabr request, we should two buffered ranges for the format (1st is segments 1, 2nd for segments 2-9)
        last_request_vpabr = rh.request_history[-1].vpabr
        video_buffered_ranges = [br for br in last_request_vpabr.buffered_ranges if br.format_id == format_init_part.format_id]
        assert len(video_buffered_ranges) == 2

    def test_multiple_buffered_ranges_server_returned_wrong_segment(self, logger, client_info):
        # Should handle multiple buffered ranges correctly,
        # where if there is another buffered range at the end of a buffered range, it should skip ahead to the end of it.
        # This can happen for live streams and resuming playback.
        # Using video-only to keep this test simple
        # This test simulates the server returning the wrong segment after seeking to the end of the consumed ranges
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        # Get all the segments from the first iteration. We need to know the timings of each to set up buffered ranges.
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        # Get all the media init parts
        media_init_parts = [part for part in iter_parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts) == DEFAULT_NUM_VIDEO_SEGMENTS + 1

        #  Now set up buffered ranges to skip some segments
        consumed_ranges = [
            # Mark middle segments as buffered (2-8). We'll get the server to return segment 10 incorrectly.
            ConsumedRange(
                # Note: First segment is init segment with no sequence number
                start_sequence_number=media_init_parts[2].sequence_number,
                end_sequence_number=media_init_parts[-3].sequence_number,
                start_time_ms=media_init_parts[2].start_time_ms,
                duration_ms=sum(part.duration_ms for part in media_init_parts[2:-2]),
            ),
        ]

        class SkipSegmentNineProcessor(BasicAudioVideoProfile):
            def buffered_segments(self, vpabr: VideoPlaybackAbrRequest, total_segments: int, format_id: FormatId):
                segments = super().buffered_segments(vpabr, total_segments, format_id)
                if segments:
                    segments.add(9)
                return segments

        # Reset the sabr stream and set the consumed ranges
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=SkipSegmentNineProcessor(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        # Start streaming until get the initialized format
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        sabr_stream.processor.initialized_formats[str(format_init_part.format_id)].consumed_ranges = consumed_ranges
        # Continue retrieving parts until we get an error
        parts = [format_init_part]
        with pytest.raises(
            MediaSegmentMismatchError,
            match=r'Segment sequence number mismatch for format FormatId\(itag=248, lmt=456, xtags=None\): expected 9, received 10',
        ):
            for part in iter_parts:
                parts.append(part)

        # Expect that the only media init parts we get is init segment, first segment
        media_init_parts_received = [part for part in parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts_received) == 2
        assert media_init_parts_received[0].sequence_number is None  # init segment
        assert media_init_parts_received[1].sequence_number == 1

        # In the last vpabr request, we should two buffered ranges for the format (1st is segments 1, 2nd for segments 2-9)
        last_request_vpabr = rh.request_history[-1].vpabr
        video_buffered_ranges = [br for br in last_request_vpabr.buffered_ranges if br.format_id == format_init_part.format_id]
        assert len(video_buffered_ranges) == 2

    def test_previous_segment_and_current_consumed_wrong_segment(self, logger, client_info):
        # Should throw a segment mismatch error if the previous segment and the current
        # are consumed but are not in the same consumed range chain (i.e, out of order)
        # This case probably would only occur on the first request on resume and would be a server error
        # For example, we have populated the following consumed ranges after format initialization:
        # -- -- [CR: 3-9]
        # After retrieving the first segment, we have two consumed ranges:
        # [CR: 1] -- [CR: 3-9] --
        # The next expected segment is 2, but if the server returns segment 3 or higher instead of segment 2,
        # it should error with a segment mismatch.
        # Otherwise, the server could followup with segment 10, which could be accepted, returned and corrupt the file:
        # [CR: 1] -- [CR: 3-10]

        init_sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        # Get all the segments from the first iteration. We need to know the timings of each to set up buffered ranges.
        iter_parts = init_sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        # Get all the media init parts
        media_init_parts = [part for part in iter_parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts) == DEFAULT_NUM_VIDEO_SEGMENTS + 1

        # Set up buffered ranges to skip from segment 3 - 9
        consumed_ranges = [
            ConsumedRange(
                # Note: First segment is init segment with no sequence number
                start_sequence_number=media_init_parts[3].sequence_number,
                end_sequence_number=media_init_parts[-2].sequence_number,
                start_time_ms=media_init_parts[3].start_time_ms,
                duration_ms=sum(part.duration_ms for part in media_init_parts[3:-1]),
            ),
        ]

        sabr_stream, rh, _ = setup_sabr_stream_av(
            # Increase max segments per request to 3 so we get init + 2 segments on first request
            sabr_response_processor=SkipSegmentProfile({'max_segments': 3, 'skip_segments': {2}}),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )
        # Start streaming until get the initialized format
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        sabr_stream.processor.initialized_formats[str(format_init_part.format_id)].consumed_ranges.extend(consumed_ranges)
        # Continue retrieving parts until we get an error
        parts = [format_init_part]
        with pytest.raises(
            UnexpectedConsumedMediaSegment,
            match=r'Unexpected consumed segment received for format FormatId\(itag=248, lmt=456, xtags=None\): sequence number 3 \(not in expected consumed range\)',
        ):
            for part in iter_parts:
                parts.append(part)

        initialized_format = sabr_stream.processor.initialized_formats[str(format_init_part.format_id)]
        # Previous segment should still be segment 1
        assert initialized_format.previous_segment.sequence_number == 1

        # Should have failed on the first request
        assert len(rh.request_history) == 1

        result_consumed_ranges = initialized_format.consumed_ranges
        assert len(result_consumed_ranges) == 2
        # One of the consumed ranges should equal the original consumed range.
        # If the error did not occur, then we would likely have retrieved segment 10 too.
        assert consumed_ranges[0] in result_consumed_ranges
        # The other consumed range should be for segment 1
        assert ConsumedRange(
            start_sequence_number=1,
            end_sequence_number=1,
            start_time_ms=0,
            duration_ms=1000,
        ) in result_consumed_ranges

        # We should not have received segment 2 or 3 from SabrStream
        media_init_parts_received = [part for part in parts if isinstance(part, MediaSegmentInitSabrPart)]
        received_sequence_numbers = [part.sequence_number for part in media_init_parts_received]
        assert 2 not in received_sequence_numbers
        assert 3 not in received_sequence_numbers

    def test_server_format_change_error(self, logger, client_info):
        # Should raise an error if the server changes the format IDs mid-stream
        processor = BasicAudioVideoProfile()
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=processor,
            client_info=client_info,
            logger=logger,
        )

        # Get first few parts to trigger first request
        parts_iter = sabr_stream.iter_parts()
        next(parts_iter)

        # Make the server change the audio format ID on the next request
        processor.options['default_audio_format'] = FormatId(itag=141, lmt=789)

        # Expect an error when continuing to retrieve parts
        with pytest.raises(
            SabrStreamError,
            match=r'Server changed format. Changing formats is not currently supported',
        ):
            # Continue retrieving parts until error is raised
            list(parts_iter)

    def test_video_only_audio_format_changed(self, logger, client_info):
        # Should not error if the audio format changes when video-only is requested.
        # This can happen as the client requests a specific video format but not audio (as it is discarded).

        processor = BasicAudioVideoProfile()
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=processor,
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )
        _, video_selector = selectors
        parts_iter = sabr_stream.iter_parts()
        parts = [next(parts_iter)]
        # Make the server change the audio format ID on the next request
        processor.options['default_audio_format'] = FormatId(itag=141, lmt=789)
        # Continue retrieving parts; should not raise
        parts.extend(parts_iter)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        # Should not be any audio parts
        audio_parts = [part for part in parts if hasattr(part, 'format_selector') and isinstance(part.format_selector, AudioSelector)]
        assert not audio_parts

    def test_request_number(self, logger, client_info):
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

    def test_request_headers(self, logger, client_info):
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

    def test_basic_redirect(self, logger, client_info):
        # Test successful redirect handling
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=SabrRedirectAVProfile(),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors

        assert sabr_stream.url == VALID_SABR_URL
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 7
        assert rh.request_history[0].request.url == VALID_SABR_URL + '&rn=1'
        assert rh.request_history[2].request.url == 'https://redirect.googlevideo.com/sabr?sabr=1&rn=3'
        assert rh.request_history[3].request.url == 'https://redirect.googlevideo.com/final?sabr=1&rn=4'
        assert rh.request_history[4].request.url == 'https://redirect.googlevideo.com/final?sabr=1&rn=5'
        assert sabr_stream.url == 'https://redirect.googlevideo.com/final?sabr=1'

    def test_reject_http_url(self, logger, client_info):
        # Do not allow HTTP URLs for server_abr_streaming_url
        rh = SabrRequestHandler(sabr_response_processor=BasicAudioVideoProfile())
        audio_selector = AudioSelector(display_name='audio')
        video_selector = VideoSelector(display_name='video')
        with pytest.raises(InvalidSabrUrl, match='Invalid SABR URL: not a valid https url'):
            SabrStream(
                urlopen=rh.send,
                server_abr_streaming_url='http://test.googlevideo.com/sabr?sabr=1',
                logger=logger,
                video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
                client_info=client_info,
                audio_selection=audio_selector,
                video_selection=video_selector,
            )

    def test_url_update(self, logger, client_info):
        # Should allow the caller to update the URL mid-stream and use it
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.url == VALID_SABR_URL

        new_sabr_url = 'https://new.googlevideo.com/sabr?sabr=1'

        assert new_sabr_url != VALID_SABR_URL

        # Retrieve 4 requests (based on request_history)
        parts = []
        parts_iter = sabr_stream.iter_parts()
        while len(rh.request_history) < 4:
            parts.append(next(parts_iter))
        # Update the URL
        sabr_stream.url = new_sabr_url
        assert sabr_stream.url == new_sabr_url
        # Continue retrieving parts
        parts.extend(list(parts_iter))
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 6
        assert rh.request_history[0].request.url == VALID_SABR_URL + '&rn=1'
        assert rh.request_history[1].request.url == VALID_SABR_URL + '&rn=2'
        assert rh.request_history[2].request.url == VALID_SABR_URL + '&rn=3'
        assert rh.request_history[3].request.url == VALID_SABR_URL + '&rn=4'
        assert rh.request_history[4].request.url == new_sabr_url + '&rn=5'
        assert rh.request_history[5].request.url == new_sabr_url + '&rn=6'
        assert sabr_stream.url == new_sabr_url

    def test_close_prevents_iteration(self, logger, client_info):
        # If the stream is closed before iteration, it should be marked as consumed
        # and any attempt to use it should raise SabrStreamConsumedError
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )

        sabr_stream.close()

        with pytest.raises(SabrStreamConsumedError, match='SABR stream has already been consumed'):
            list(sabr_stream.iter_parts())
        assert not rh.request_history

    def test_create_stats_str_vod(self, logger, client_info):
        # Test that the stats string is created correctly for VOD stream
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )

        initial_str = sabr_stream.create_stats_str()
        assert initial_str == 'v:unknown c:WEB t:0 h:test exp:n/a rn:0 sr:0 act:N pot:N sps:n/a vod if:[none] cr:[none]'
        list(sabr_stream.iter_parts())

        final_str = sabr_stream.create_stats_str()
        assert final_str == 'v:unknown c:WEB t:10001 h:test exp:n/a rn:6 sr:0 act:Y pot:N sps:n/a vod if:[140(5), 248(10)] cr:[140:1-5 (0-10001), 248:1-10 (0-10001)]'

    def test_create_stats_str_vod_discard(self, logger, client_info):
        # Test that the stats string is created correctly for VOD stream
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        initial_str = sabr_stream.create_stats_str()
        assert initial_str == 'v:unknown c:WEB t:0 h:test exp:n/a rn:0 sr:0 act:N pot:N sps:n/a vod if:[none] cr:[none]'
        list(sabr_stream.iter_parts())

        final_str = sabr_stream.create_stats_str()
        assert final_str == 'v:unknown c:WEB t:10001 h:test exp:n/a rn:6 sr:0 act:Y pot:N sps:n/a vod if:[140d(5), 248(10)] cr:[140:0-9007199254740991 (0-9007199254740991), 248:1-10 (0-10001)]'

    def test_no_print_stats_no_debug(self, logger, client_info):
        # Should not print stats during the stream
        logger.log_level = logger.LogLevel.INFO
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        initial_stats = sabr_stream.create_stats_str()
        list(sabr_stream.iter_parts())
        with pytest.raises(AssertionError):
            logger.debug.assert_any_call(f'[SABR State] {initial_stats}')

    def test_print_stats_debug(self, logger, client_info):
        # Should print stats during the stream if log level is set to debug
        logger.log_level = logger.LogLevel.DEBUG
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        initial_stats = sabr_stream.create_stats_str()
        list(sabr_stream.iter_parts())

        # should print stats during the stream
        logger.debug.assert_any_call(f'[SABR State] {initial_stats}')

        # last stats state should indicate end of stream with all segments retrieved
        final_str = sabr_stream.create_stats_str()
        logger.debug.assert_any_call(f'[SABR State] {final_str}')

    def test_consumed_after_full_iteration(self, logger, client_info):
        # After fully consuming the stream, any attempt to use it should raise SabrStreamConsumedError
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        list(sabr_stream.iter_parts())

        # Further attempts to iterate should raise
        with pytest.raises(SabrStreamConsumedError):
            list(sabr_stream.iter_parts())

    def test_close_mid_iteration_stops(self, logger, client_info):
        # Closing the stream mid-iteration should mark the stream as consumed
        # and only yield remaining parts from the current response.
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        parts_iter = sabr_stream.iter_parts()
        # First part from first request
        next(parts_iter)
        requests_before_close = len(rh.request_history)

        sabr_stream.close()
        # Get remaining parts from current response
        list(parts_iter)
        # No additional requests should have been made after close
        assert len(rh.request_history) == requests_before_close
        with pytest.raises(SabrStreamConsumedError):
            list(sabr_stream.iter_parts())

    def test_iterator(self, logger, client_info):
        # Should allow SabrStream to be used as an interator directly
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream)
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    @pytest.mark.parametrize(
        'bad_url',
        [None, '', 'bad-url%', 'http://insecure.googlevideo.com?sabr=1', 'file:///etc/passwd', 'https://example.org/sabr'],
        ids=['none', 'empty', 'malformed', 'insecure', 'file scheme', 'different domain'])
    def test_update_url_invalid(self, logger, client_info, bad_url):
        # Should reject invalid URLs relative to the current URL when updating sabr_stream.url
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        assert sabr_stream.url == VALID_SABR_URL

        with pytest.raises(InvalidSabrUrl, match=r'Invalid SABR URL:'):
            sabr_stream.url = bad_url

        assert sabr_stream.url == VALID_SABR_URL

    @pytest.mark.parametrize(
        'bad_url',
        [None, '', 'bad-url%', 'http://insecure.googlevideo.com?sabr=1', 'file:///etc/passwd', 'https://example.org/sabr'],
        ids=['none', 'empty', 'malformed', 'insecure', 'file scheme', 'different domain'])
    def test_process_redirect_invalid_url(self, logger, client_info, bad_url):
        # Should validate redirect urls
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=SabrRedirectAVProfile({'redirects': {2: {'url': bad_url, 'replace': True}}}),
            client_info=client_info,
            logger=logger,
        )
        with pytest.raises(InvalidSabrUrl, match=r'Invalid SABR URL:'):
            list(sabr_stream.iter_parts())

        assert sabr_stream.url == VALID_SABR_URL

    def test_set_live_from_url_source(self, logger, client_info):
        # Should set is_live to True based on source URL parameter
        valid_live_url_with_source = 'https://live.googlevideo.com/sabr?source=yt_live_broadcast&sabr=1'
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url=valid_live_url_with_source,
        )
        assert sabr_stream.url == valid_live_url_with_source
        assert sabr_stream.processor.is_live is True

    def test_not_set_live_from_url_no_source(self, logger, client_info):
        valid_live_url_without_source = 'https://live.googlevideo.com/sabr?source=another_source&sabr=1'
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url=valid_live_url_without_source,
        )
        assert sabr_stream.url == valid_live_url_without_source
        assert sabr_stream.processor.is_live is False

    def test_nonlive_ignore_broadcast_id_update(self, logger, client_info):
        # Should ignore broadcast_id updates in URL when non-live
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url=VALID_SABR_URL + '&id=1',
        )

        assert sabr_stream.processor.is_live is False
        sabr_stream.url = VALID_SABR_URL + '&id=2'
        assert sabr_stream.processor.is_live is False
        assert sabr_stream.url == VALID_SABR_URL + '&id=2'

    @pytest.mark.parametrize('post_live', [True, False], ids=['post_live=True', 'post_live=False'])
    def test_live_error_on_broadcast_id_update(self, logger, client_info, post_live):
        # Should raise an error if broadcast_id changes for live stream. Post live flag should not affect this.
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://live.googlevideo.com/sabr?sabr=1&source=yt_live_broadcast&id=xyz.1',
            post_live=post_live,
        )

        assert sabr_stream.processor.is_live is True
        with pytest.raises(BroadcastIdChanged, match=r'Broadcast ID changed from 1 to 2\. The download will need to be restarted\.'):
            sabr_stream.url = 'https://live.googlevideo.com/sabr?sabr=1&source=yt_live_broadcast&id=xyz.2'

    def test_reload_player_response(self, logger, client_info):
        # Should yield a RefreshPlayerResponseSabrPart when instructed to reload the player response
        def inject_reload_player_response(parts, vpabr, url, request_number):
            if request_number == 1:
                payload = protobug.dumps(ReloadPlayerResponse(
                    reload_playback_params=ReloadPlaybackParams(token='test token'),
                ))
                return [
                    *parts,
                    UMPPart(
                        part_id=UMPPartId.RELOAD_PLAYER_RESPONSE,
                        size=len(payload),
                        data=io.BytesIO(payload),
                    ),
                ]
            return parts

        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            sabr_response_processor=CustomAVProfile({'custom_parts_function': inject_reload_player_response}),
        )
        # Retrieve parts until we get a RefreshPlayerResponseSabrPart
        refresh_part = None
        for part in sabr_stream.iter_parts():
            if isinstance(part, RefreshPlayerResponseSabrPart):
                refresh_part = part
                break
        assert refresh_part is not None
        assert refresh_part.reason == RefreshPlayerResponseSabrPart.Reason.SABR_RELOAD_PLAYER_RESPONSE
        assert refresh_part.reload_playback_token == 'test token'

    def test_nonlive_segment_mismatch_error(self, logger, client_info):
        # Should raise an error on segment sequence mismatch for non-live streams
        def skip_segment_func(parts, vpabr, url, request_number):
            # Skip the first media segment on second request
            if request_number == 2:
                # Skip the first media_header, media, media_end parts in request
                # Should be the first three parts
                return parts[3:]
            return parts

        sabr_stream, rh, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            sabr_response_processor=CustomAVProfile({'custom_parts_function': skip_segment_func}),
        )

        with pytest.raises(
            MediaSegmentMismatchError,
            match=r'Segment sequence number mismatch for format FormatId\(itag=140, lmt=123, xtags=None\): expected 2, received 3',
        ) as exc_info:
            list(sabr_stream.iter_parts())

        assert exc_info.value.expected_sequence_number == 2
        assert exc_info.value.received_sequence_number == 3

        # Should have made two requests before failing
        assert len(rh.request_history) == 2

    # TODO: should consider more tests where selectors are not matched / used
    #  In particular, a test where audio+video selectors provided but only one format is returned
    #  In this case, it should error (could be due to missing new segments due to not incrementing player time)
    def test_briefly_missing_initialized_format(self, logger, client_info):
        # Should not increment player_time_ms if one of the initialized formats is missing when the other has received a segment.
        # This can happen in the case we get first IF with a segment, then get a read error, then on next request is a redirect.

        def missing_format_func(parts, vpabr, url, request_number):
            # On first request, add an error after 4th part
            if request_number == 1:
                return [
                    # First format IF + init segment + first segment for that format to create a CR
                    parts[0], *parts[2:8],
                    # So error doesn't occur on reading segment data
                    UMPPart(
                        part_id=UMPPartId.SNACKBAR_MESSAGE,
                        size=0,
                        data=io.BytesIO(b''),
                    ),
                    TransportError('simulated transport error'),
                ]

            if request_number == 2:
                # On second request, return a redirect
                payload = protobug.dumps(SabrRedirect(
                    redirect_url='https://redirect.googlevideo.com/sabr?sabr=1'))
                return [
                    UMPPart(
                        part_id=UMPPartId.SABR_REDIRECT,
                        size=len(payload),
                        data=io.BytesIO(payload),
                    )]
            return parts

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            sabr_response_processor=CustomAVProfile({'custom_parts_function': missing_format_func}),
        )
        # Should not error
        parts = list(sabr_stream.iter_parts())

        audio_selector, video_selector = selectors

        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        third_request = rh.request_history[2]
        assert len(third_request.vpabr.buffered_ranges) == 1
        assert third_request.vpabr.client_abr_state.player_time_ms == 0

        logger.debug.assert_any_call('Skipping player time increment; not all enabled format selectors have an initialized format yet')

    def test_unexpected_segment_at_start_nonlive(self, logger, client_info):
        # Should error if the first segment received for a non-live stream is not sequence number 1 when start_time_ms is 0
        # (Guard to prevent missing segments at start of non-live streams)
        sabr_stream, rh, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            sabr_response_processor=SkipSegmentProfile({'skip_segments': {1}}),
        )
        with pytest.raises(
            MediaSegmentMismatchError,
            match=r'Segment sequence number mismatch for format FormatId\(itag=140, lmt=123, xtags=None\): expected 1, received 2',
        ) as exc_info:
            list(sabr_stream.iter_parts())

        assert exc_info.value.expected_sequence_number == 1
        assert exc_info.value.received_sequence_number == 2

        assert len(rh.request_history) == 1
        assert rh.request_history[0].vpabr.client_abr_state.player_time_ms == 0

    def test_unexpected_segment_at_start_resume_nonlive(self, logger, client_info):
        # Should error if the first segment received for a non-live stream
        # when resuming is not in the first consumed range chain

        # 1. Get all the segments to get the timings
        init_sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )
        iter_parts = init_sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        # Get all the media init parts
        media_init_parts = [part for part in iter_parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts) == DEFAULT_NUM_VIDEO_SEGMENTS + 1

        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            sabr_response_processor=SkipSegmentProfile({'skip_segments': {1, 2, 3}}),
            enable_audio=False,
        )

        # Mark segments 1 and 2 as buffered (with two consumed ranges)
        consumed_ranges = [
            # Note: First segment is init segment with no sequence number
            ConsumedRange(
                start_sequence_number=1,
                end_sequence_number=1,
                start_time_ms=media_init_parts[1].start_time_ms,
                duration_ms=media_init_parts[1].duration_ms,
            ),
            ConsumedRange(
                start_sequence_number=2,
                end_sequence_number=2,
                start_time_ms=media_init_parts[2].start_time_ms,
                duration_ms=media_init_parts[2].duration_ms,
            ),
        ]

        # Start streaming until get the initialized format
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        sabr_stream.processor.initialized_formats[str(format_init_part.format_id)].consumed_ranges = consumed_ranges

        with pytest.raises(
            MediaSegmentMismatchError,
            match=r'Segment sequence number mismatch for format FormatId\(itag=248, lmt=456, xtags=None\): expected 3, received 4',
        ) as exc_info:
            list(iter_parts)
        assert exc_info.value.expected_sequence_number == 3
        assert exc_info.value.received_sequence_number == 4

    def test_player_time_ms_start_nonzero_nonlive(self, logger, client_info):
        # Should respect start_time_ms on non-live streams
        initial_player_time_ms = 5000  # 5 seconds

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            sabr_response_processor=BasicAudioVideoProfile(),
            start_time_ms=initial_player_time_ms,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        skipped_audio_segments = 2
        skipped_video_segments = 4

        assert_media_sequence_in_order(
            parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1 - skipped_audio_segments, start_sequence_number=skipped_audio_segments + 1)
        assert_media_sequence_in_order(
            parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1 - skipped_video_segments, start_sequence_number=skipped_video_segments + 1)

        # In the first request, player_time_ms should be 5000
        first_request = rh.request_history[0]
        assert first_request.vpabr.client_abr_state.player_time_ms == initial_player_time_ms
