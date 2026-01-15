from __future__ import annotations
import base64
import io
import time
from unittest.mock import MagicMock
import protobug
import pytest
from yt_dlp import YoutubeDL
from yt_dlp.downloader.sabr._logger import SabrFDLogger
from test.test_sabr.test_stream.helpers import (
    VIDEO_PLAYBACK_USTREAMER_CONFIG,
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    extract_rn,
    SabrRequestHandler,
    BasicAudioVideoProfile,
    SabrRedirectAVProfile,
    RequestRetryAVProfile,
    CustomAVProfile,
    assert_media_sequence_in_order,
    create_inject_read_error,
    AdWaitAVProfile,
    SabrContextSendingPolicyAVProfile,
    PoTokenAVProfile,
    LiveAVProfile,
)
from yt_dlp.extractor.youtube._proto.videostreaming.reload_player_response import ReloadPlaybackParams
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import (
    SabrStreamError,
    PoTokenError,
    SabrStreamConsumedError,
    MediaSegmentMismatchError,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart
from yt_dlp.networking.exceptions import TransportError, HTTPError, RequestError

from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector, ConsumedRange, SabrLogger
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    FormatInitializedSabrPart,
    RefreshPlayerResponseSabrPart,
    PoTokenStatusSabrPart,
    MediaSegmentInitSabrPart,
    MediaSeekSabrPart,
    MediaSegmentEndSabrPart,
)
from yt_dlp.extractor.youtube._streaming.sabr.stream import SabrStream
from yt_dlp.extractor.youtube._proto.videostreaming import (
    FormatId,
    BufferedRange,
    TimeRange,
    SabrError,
    SabrContext,
    ReloadPlayerResponse,
    SabrRedirect,
)
from yt_dlp.utils import parse_qs


def setup_sabr_stream_av(
    url='https://example.com/sabr',
    sabr_response_processor=None,
    client_info=None,
    logger=None,
    enable_audio=True,
    enable_video=True,
    **options,
):
    rh = SabrRequestHandler(sabr_response_processor=sabr_response_processor or BasicAudioVideoProfile())
    audio_selector = AudioSelector(display_name='audio') if enable_audio else None
    video_selector = VideoSelector(display_name='video') if enable_video else None
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

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        _, video_selector = selectors

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

        # We should have got a MediaSeekSabrPart with a reason of CONSUMED_SEEK for the given format
        seek_parts = [part for part in parts if isinstance(part, MediaSeekSabrPart)]
        assert len(seek_parts) == 1
        seek_part = seek_parts[0]
        assert seek_part.reason == MediaSeekSabrPart.Reason.CONSUMED_SEEK
        assert seek_part.format_id == format_init_part.format_id
        assert seek_part.format_selector == video_selector

        # Should have logged to debug about the seek
        logger.debug.assert_any_call('Found two or more consumed ranges that line up, allowing a seek for format FormatId(itag=248, lmt=456, xtags=None)')

        # In the last vpabr request, we should two buffered ranges for the format (1st is segments 1, 2nd for segments 2-9)
        last_request_vpabr = rh.request_history[-1].vpabr
        video_buffered_ranges = [br for br in last_request_vpabr.buffered_ranges if br.format_id == format_init_part.format_id]
        assert len(video_buffered_ranges) == 2

    def test_fail_segment_multiple_consumed_ranges(self, logger, client_info):
        # Should bail out if a segment is in multiple consumed ranges
        # This is a guard against an internal error when setting consumed ranges
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
            enable_audio=False,
        )

        # Get the first complete segment for the format to update the consumed range
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)

        # Get first two media_end parts (init and first segment)
        first_two_media_end_parts = []
        for part in iter_parts:
            if isinstance(part, MediaSegmentEndSabrPart):
                first_two_media_end_parts.append(part)
                if len(first_two_media_end_parts) == 2:
                    break

        # Consumed range should contain the first segment
        consumed_ranges = sabr_stream.processor.initialized_formats[str(format_init_part.format_id)].consumed_ranges
        assert len(consumed_ranges) == 1
        assert consumed_ranges[0].start_sequence_number == consumed_ranges[0].end_sequence_number == 1

        # Now add another consumed range that also contains the first segment
        consumed_ranges.append(
            ConsumedRange(
                start_sequence_number=1,
                end_sequence_number=2,
                start_time_ms=0,
                duration_ms=5000,
            ))

        # Continue retrieving parts and expect error before next request
        with pytest.raises(
            SabrStreamError,
            match=r'Segment 1 for format FormatId\(itag=248, lmt=456, xtags=None\) in 2 consumed ranges',
        ):
            list(iter_parts)

        # There should have only been one request made (the initial one)
        assert len(rh.request_history) == 1

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

    def test_sps_ok(self, logger, client_info):
        # Should not fail on SPS OK status (when po token is provided)
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=PoTokenAVProfile({'sps_status': PoTokenStatusSabrPart.PoTokenStatus.OK}),
            client_info=client_info,
            logger=logger,
        )
        sabr_stream.processor.po_token = base64.b64encode(b'valid-po-token')
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)
        assert len(rh.request_history) == 6

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

        assert sabr_stream.url == 'https://example.com/sabr'
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 7
        assert rh.request_history[0].request.url == 'https://example.com/sabr?rn=1'
        assert rh.request_history[2].request.url == 'https://redirect.example.com/sabr?rn=3'
        assert rh.request_history[3].request.url == 'https://redirect.example.com/final?rn=4'
        assert rh.request_history[4].request.url == 'https://redirect.example.com/final?rn=5'
        assert sabr_stream.url == 'https://redirect.example.com/final'

    def test_reject_http_url(self, logger, client_info):
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

    def test_url_update(self, logger, client_info):
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
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 6
        assert rh.request_history[0].request.url == 'https://example.com/sabr?rn=1'
        assert rh.request_history[1].request.url == 'https://example.com/sabr?rn=2'
        assert rh.request_history[2].request.url == 'https://example.com/sabr?rn=3'
        assert rh.request_history[3].request.url == 'https://example.com/sabr?rn=4'
        assert rh.request_history[4].request.url == 'https://new.example.com/sabr?rn=5'
        assert rh.request_history[5].request.url == 'https://new.example.com/sabr?rn=6'
        assert sabr_stream.url == 'https://new.example.com/sabr'

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
        [None, '', 'bad-url%', 'http://insecure.example.com', 'file:///etc/passwd', 'https://example.org/sabr'],
        ids=['none', 'empty', 'malformed', 'insecure', 'file scheme', 'different domain'])
    def test_update_url_invalid(self, logger, client_info, bad_url):
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
    def test_process_redirect_invalid_url(self, logger, client_info, bad_url):
        # Should ignore an invalid redirect URl and continue with the current URL
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=SabrRedirectAVProfile({'redirects': {2: {'url': bad_url, 'replace': True}}}),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)
        assert len(rh.request_history) == 7
        assert sabr_stream.url == 'https://example.com/sabr'
        logger.warning.assert_any_call(f'Server requested to redirect to an invalid URL: {bad_url}')

    def test_set_live_from_url_source(self, logger, client_info):
        # Should set is_live to True based on source URL parameter
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr?source=yt_live_broadcast',
        )
        assert sabr_stream.url == 'https://example.com/sabr?source=yt_live_broadcast'
        assert sabr_stream.processor.is_live is True

    def test_nonlive_ignore_broadcast_id_update(self, logger, client_info):
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
    def test_live_error_on_broadcast_id_update(self, logger, client_info, post_live):
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
                    redirect_url='https://redirect.example.com/sabr'))
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

        # TODO: currently fails as the player_time_ms is increased
        # TODO: SabrStream should have also detect the video format is missing the first segment...
        #  it should pin expected segment to 1
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        third_request = rh.request_history[2]
        assert len(third_request.vpabr.buffered_ranges) == 1
        assert third_request.vpabr.client_abr_state.player_time_ms == 0

    class TestStreamStall:
        # TODO: Create a custom error for this case instead of using SabrStreamError (e.g StreamStallError)
        def test_no_new_segments_default(self, logger, client_info):
            # TODO: currently fails on max_empty_requests+1, should be max_empty_requests
            # Should raise SabrStreamError if no new segments are received on the third request (default)
            def no_new_segments_func(parts, vpabr, url, request_number):
                # On third request, return only init parts (no new segments)
                if request_number >= 4:
                    return parts
                return []

            sabr_stream, rh, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_func}),
            )
            with pytest.raises(SabrStreamError, match=r'No new segments received from server in 3 consecutive requests'):
                list(sabr_stream.iter_parts())

            # Should have made 3 requests before failing
            assert len(rh.request_history) == 3

        def test_no_new_segments_custom(self, logger, client_info):
            # Should raise SabrStreamError if no new segments are received on the fifth request (custom)
            max_empty_requests = 5

            def no_new_segments_func(parts, vpabr, url, request_number):
                # On fifth request, return only init parts (no new segments)
                if request_number > max_empty_requests:
                    return parts
                return []

            sabr_stream, rh, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_func}),
                max_empty_requests=max_empty_requests,
            )
            with pytest.raises(SabrStreamError, match=r'No new segments received from server in 5 consecutive requests'):
                list(sabr_stream.iter_parts())

            # Should have made 5 requests before failing
            assert len(rh.request_history) == 5

        def test_no_new_segments_reset_on_new_segment(self, logger, client_info):
            # Should reset the empty request counter when a new segment is received
            max_empty_requests = 3

            def no_new_segments_func(parts, vpabr, url, request_number):
                # On every third request, return parts (new segments)
                if request_number % max_empty_requests == 0:
                    return parts
                return []

            sabr_stream, rh, selectors = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_func}),
                max_empty_requests=max_empty_requests,
            )
            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            # Should have made 6 requests total (2 sets of 3)
            assert len(rh.request_history) == 6 * max_empty_requests
            audio_selector, video_selector = selectors
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            logger.trace.assert_any_call('No new segments received in request 1, count: 1')
            logger.trace.assert_any_call('No new segments received in request 2, count: 2')
            assert rh.request_history[0].parts == rh.request_history[1].parts == []
            assert rh.request_history[2].parts
            logger.trace.assert_any_call('No new segments received in request 4, count: 1')
            logger.trace.assert_any_call('No new segments received in request 5, count: 2')
            assert rh.request_history[3].parts == rh.request_history[4].parts == []
            assert rh.request_history[5].parts

        def test_max_empty_requests_negative(self, logger, client_info):
            # Should raise ValueError if max_empty_requests is negative
            with pytest.raises(ValueError, match='max_empty_requests must be greater than 0'):
                setup_sabr_stream_av(
                    client_info=client_info,
                    logger=logger,
                    max_empty_requests=-1,
                )

        def test_no_new_segments_http_retry_then_segments(self, logger, client_info):
            # Receive a TransportError during response on the 3rd attempt with no new segments,
            # should retry and continue if retried request returns new segments
            max_empty_requests = 3

            def no_new_segments_with_error_func(parts, vpabr, url, request_number):
                # On third request, raise TransportError
                if request_number == max_empty_requests:
                    return [TransportError('simulated transport error')]
                # On 4th request (retried), return parts (new segments)
                if request_number > max_empty_requests:
                    return parts
                return []

            sabr_stream, rh, selectors = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_with_error_func}),
                max_empty_requests=max_empty_requests,
            )
            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert len(rh.request_history) == 6 + max_empty_requests
            audio_selector, video_selector = selectors
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            assert rh.request_history[0].parts == rh.request_history[1].parts == []
            assert isinstance(rh.request_history[2].error, TransportError)
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')

        def test_no_new_segments_http_retry_no_segments(self, logger, client_info):
            # Receive a TransportError during response on the 3rd attempt with no new segments,
            # should retry and fail if retried request also returns no new segments
            max_empty_requests = 3

            def no_new_segments_with_error_func(parts, vpabr, url, request_number):
                # On third request, raise TransportError
                if request_number == max_empty_requests:
                    return [TransportError('simulated transport error')]
                return []

            sabr_stream, rh, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_with_error_func}),
                max_empty_requests=max_empty_requests,
            )
            with pytest.raises(SabrStreamError, match=r'No new segments received from server in 3 consecutive requests'):
                list(sabr_stream.iter_parts())

            # Should have made 4 requests before failing (3 empty + 1 retried)
            assert len(rh.request_history) == max_empty_requests + 1

            assert rh.request_history[0].parts == rh.request_history[1].parts == []
            assert isinstance(rh.request_history[2].error, TransportError)
            assert rh.request_history[3].parts == []

        def test_no_new_segments_http_retry_with_segments_reset(self, logger, client_info):
            # TODO: currently fails as we do not reset the empty counter if we received an error and retry
            # Receive a TransportError during response on the 3rd attempt WITH new segments (before the TransportError)
            # should retry and continue, resetting the empty request counter
            max_empty_requests = 3

            def no_new_segments_with_error_func(parts, vpabr, url, request_number):
                # On every third request, return parts (new segments) with an error
                if request_number % max_empty_requests == 0:
                    return [*parts,
                            # Dummy part as otherwise would fail on last media_end part
                            UMPPart(
                                part_id=UMPPartId.SNACKBAR_MESSAGE,
                                size=0,
                                data=io.BytesIO(b''),
                            ), TransportError('simulated transport error')]
                return []

            sabr_stream, rh, selectors = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_with_error_func}),
                max_empty_requests=max_empty_requests,
            )
            # Should complete successfully
            parts = list(sabr_stream.iter_parts())

            audio_selector, video_selector = selectors
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Should have made 6 requests total (2 sets of 3) + 1 for (empty) retry at the end
            assert len(rh.request_history) == 6 * max_empty_requests + 1
            assert rh.request_history[0].parts == rh.request_history[1].parts == []
            logger.trace.assert_any_call('No new segments received in request 1, count: 1')
            logger.trace.assert_any_call('No new segments received in request 2, count: 2')
            assert isinstance(rh.request_history[2].error, TransportError)
            assert rh.request_history[2].parts  # Has new segments

            assert rh.request_history[3].parts == rh.request_history[4].parts == []
            logger.trace.assert_any_call('No new segments received in request 4, count: 1')
            logger.trace.assert_any_call('No new segments received in request 5, count: 2')
            assert isinstance(rh.request_history[5].error, TransportError)
            assert rh.request_history[5].parts  # Has new segments

            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')

        def test_consumed_segments_counted(self, logger, client_info):
            # Requests with only consumed segments should count towards empty requests
            max_empty_requests = 3
            second_request_parts = []

            def consumed_segments_func(parts, vpabr, url, request_number):
                # Replay the segments from the second request on all subsequent requests
                if request_number == 2:
                    second_request_parts.extend(parts)
                if request_number >= 3:
                    # rewind all the files so we can read them again
                    for part in second_request_parts:
                        if hasattr(part.data, 'seek'):
                            part.data.seek(0)
                    return second_request_parts
                return parts

            sabr_stream, rh, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                sabr_response_processor=CustomAVProfile({'custom_parts_function': consumed_segments_func}),
                max_empty_requests=max_empty_requests,
            )
            with pytest.raises(SabrStreamError, match=r'No new segments received from server in 3 consecutive requests'):
                list(sabr_stream.iter_parts())

            # Should have made 5 requests before failing (2 normal + 3 empty)
            assert len(rh.request_history) == 2 + max_empty_requests
            logger.trace.assert_any_call('No new segments received in request 3, count: 1')
            logger.trace.assert_any_call('No new segments received in request 4, count: 2')

        @pytest.mark.skip(reason='todo')
        def test_discarded_segments_not_counted(self, logger, client_info):
            # Requests with NEW segments marked as discarded (but no consumed) should NOT count towards empty requests
            # Set up a audio-only stream with discard=True in the selector

            # Create a custom function that will return a reload player response on the 1st request.
            # This allows us to catch the iterator before going onto the next request so we can clear consumed ranges.
            # (Format parts will NOT be returned as the format is marked to discard)
            def no_new_segments_discarded_func(parts, vpabr, url, request_number):
                # On 1st request, inject in ReloadPlayerResponse part
                if request_number == 1:
                    payload = protobug.dumps(ReloadPlayerResponse(
                        reload_playback_params=ReloadPlaybackParams(token='test token'),
                    ))
                    return [
                        parts[0],  # Format init part
                        UMPPart(
                            part_id=UMPPartId.RELOAD_PLAYER_RESPONSE,
                            size=len(payload),
                            data=io.BytesIO(payload),
                        ),
                        *parts[1:],  # Media parts. Needs to be after reload part so new buffered ranges created
                    ]
                return parts

            rh = SabrRequestHandler(sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_discarded_func}))
            audio_selector = AudioSelector(display_name='audio', discard_media=True)
            sabr_stream = SabrStream(
                urlopen=rh.send,
                server_abr_streaming_url='https://example.com/sabr',
                logger=logger,
                video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
                client_info=client_info,
                audio_selection=audio_selector,
            )

            # Clear the buffered ranges of the format (which will be set to fully buffered)
            parts_iter = sabr_stream.iter_parts()

            reload_player_response_part = next(parts_iter)
            assert isinstance(reload_player_response_part, RefreshPlayerResponseSabrPart)
            for format_init_part in sabr_stream.processor.initialized_formats.values():
                format_init_part.consumed_ranges.clear()

            # Get rest of parts, should not error or get any segments
            # TODO: this fails as we do not increment player_time_ms for discarded formats
            #  (so the server does not respond with any) - even if discarded formats are the only ones available?
            #  Technically this should never be a valid use case.
            # We could alternatively test this by having an enabled format that we withold segments
            # parts = list(parts_iter)

    class TestExpiry:
        def test_expiry_threshold_sec_validation(self, logger, client_info):
            # Should raise ValueError if expiry_threshold_sec is negative
            with pytest.raises(ValueError, match='expiry_threshold_sec must be greater than 0'):
                setup_sabr_stream_av(
                    client_info=client_info,
                    logger=logger,
                    expiry_threshold_sec=-10,
                )

        def test_expiry_refresh_player_response(self, logger, client_info):
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

        def test_expiry_threshold_sec(self, logger, client_info):
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

        def test_no_expiry_in_url(self, logger, client_info):
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

        def test_not_expired(self, logger, client_info):
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
        def test_retry_on_transport_error(self, logger, client_info):
            # Should retry on TransportError occurring during request
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

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

        def test_retry_on_http_5xx(self, logger, client_info):
            # Should retry on HTTP 5xx errors
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'http', 'status': 500, 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )

            parts = list(sabr_stream.iter_parts())
            audio_selector, video_selector = selectors
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

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

        def test_no_retry_on_http_4xx(self, logger, client_info):
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

        def test_no_retry_on_request_error(self, logger, client_info):
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

        def test_multiple_retries(self, logger, client_info):
            # Should retry multiple times on consecutive errors
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 3, 4]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

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

        def test_reset_retry_counter(self, logger, client_info):
            # Should reset the retry counter after a successful request
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 4]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

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

        def test_exceed_max_retries(self, logger, client_info):
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

        def test_http_retries_option(self, logger, client_info):
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

        def test_http_retry_sleep_func(self, logger, client_info):
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

        def test_expiry_on_retry(self, logger, client_info):
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

        def test_increment_rn_on_retry(self, logger, client_info):
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

    class TestResponseRetries:

        def test_retry_on_response_error(self, logger, client_info):
            # Should retry on SabrResponseError occurring during response processing
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': lambda parts, vpabr, url, request_number: [TransportError('simulated SABR response error')] if request_number == 2 else parts}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Find the first request that recorded an error
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)

            request = rh.request_history[i_err]
            assert isinstance(request.error, TransportError)
            assert request.error.msg == 'simulated SABR response error'

            # There should be a retry request recorded immediately after the error
            retried_request = rh.request_history[i_err + 1]
            assert retried_request.error is None

            # The video_playback_abr_request should be the same for both requests - no changes in state (e.g playback time)
            # (as the error was during before any parts were processed)
            assert request.request.data == retried_request.request.data

            # Should log the retry attempt
            logger.warning.assert_any_call('[sabr] Got error: simulated SABR response error. Retrying (1/10)...')

        def test_retry_read_failure_media_part(self, logger, client_info):
            # Should retry if a TransportError occurs while reading a media part
            inject_read_error = create_inject_read_error([2], part_id=UMPPartId.MEDIA)

            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
            )

            audio_selector, video_selector = selectors

            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1, allow_retry=True)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1, allow_retry=True)

            # As this is the first MEDIA part in the response,
            # the playback time should NOT have advanced, and buffered ranges should be the same.

            request = rh.request_history[1]  # The request that had the read error
            retried_request = rh.request_history[2]  # followup retried request
            assert request.request.data == retried_request.request.data

            # TODO: currently raises a partial segments warning, this is incorrect!
            logger.warning.assert_any_call('[sabr] Got error: simulated read error. Retrying (1/10)...')

        def test_retry_failure_nth_media_part(self, logger, client_info):
            # Should retry if a TransportError occurs while reading the Nth media part
            # In this case, the first media part should be processed successfully,
            # so the playback time should NOT be advanced, but buffered ranges should have been updated.
            inject_read_error = create_inject_read_error([2], part_id=UMPPartId.MEDIA, occurance=2)
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1, allow_retry=True)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1, allow_retry=True)
            # The playback time and buffered ranges should have advanced after the first media part
            request = rh.request_history[1]  # The request that had the read error
            retried_request = rh.request_history[2]  # followup retried request
            # The playback time in the retried request should be advanced by the duration of one media part
            original_vpabr = request.vpabr
            retried_vpabr = retried_request.vpabr

            # Player time should be the same as original
            assert retried_vpabr.client_abr_state.player_time_ms == original_vpabr.client_abr_state.player_time_ms

            # ONE of the buffered ranges should be one segment ahead (as these are updated after a media part is processed)
            matches = 0
            for br in original_vpabr.buffered_ranges:
                # find matching buffered range in retried_vpabr by format_id
                br_retried = next((r for r in retried_vpabr.buffered_ranges if r.format_id == br.format_id), None)
                assert br_retried is not None
                # The end of the buffered range should be advanced by one segment duration
                if br_retried.end_segment_index == br.end_segment_index + 1:
                    matches += 1
            assert matches == 1, 'Expected one buffered range to be advanced by one segment after retrying Nth media part read failure'

            # TODO: currently raises a partial segments warning, this is incorrect!
            logger.warning.assert_any_call('[sabr] Got error: simulated read error. Retrying (1/10)...')

        def test_retry_on_response_read_failure_end(self, logger, client_info):
            # Should retry if a TransportError occurs after we have read all segments in the response and video
            # We can simulate this by adding a informational part at the end that fails to read
            def inject_read_error(parts, vpabr, url, request_number):
                if request_number != 6:
                    return parts
                parts.append(UMPPart(
                    part_id=UMPPartId.SNACKBAR_MESSAGE,
                    size=0,
                    data=io.BytesIO(b''),
                ))
                return create_inject_read_error([6], part_id=UMPPartId.SNACKBAR_MESSAGE, occurance=1)(parts, vpabr, url, request_number)

            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors
            parts = list(sabr_stream.iter_parts())
            # Should not be getting any retried segments here as the error is after all media parts
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1, allow_retry=False)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1, allow_retry=False)

            assert len(rh.request_history) == 7  # Original + 1 retried request
            # The playback time and buffered ranges should have advanced
            request = rh.request_history[5]  # The request that had the read error
            retried_request = rh.request_history[6]  # followup retried request
            # The playback time in the retried request should be advanced by the duration of one media part
            original_vpabr = request.vpabr
            retried_vpabr = retried_request.vpabr

            # Player time should be the same as original
            assert retried_vpabr.client_abr_state.player_time_ms == original_vpabr.client_abr_state.player_time_ms

            # At least ONE of the buffered ranges should be one segment ahead (as these are updated after a media part is processed)
            matches = 0
            for br in original_vpabr.buffered_ranges:
                # find matching buffered range in retried_vpabr by format_id
                br_retried = next((r for r in retried_vpabr.buffered_ranges if r.format_id == br.format_id), None)
                assert br_retried is not None
                # The end of the buffered range should be advanced by one segment duration
                if br_retried.end_segment_index > br.end_segment_index:
                    matches += 1
            assert matches >= 1, 'Expected at least one buffered range to be advanced by one segment after retrying Nth media part read failure'

            logger.warning.assert_any_call('[sabr] Got error: simulated read error. Retrying (1/10)...')

    class TestSabrErrorRetries:
        def test_retry_on_sabr_error_part(self, logger, client_info):
            def sabr_error_injector(parts, vpabr, url, request_number):
                if request_number == 2:
                    message = protobug.dumps(SabrError(action=1, type='simulated SABR error'))

                    # Insert after the first MEDIA_END. SabrStream should stop processing the response at this point.
                    for i, p in enumerate(parts):
                        if p.part_id == UMPPartId.MEDIA_END:
                            parts.insert(i + 1, UMPPart(
                                part_id=UMPPartId.SABR_ERROR,
                                size=len(message),
                                data=io.BytesIO(message),
                            ))
                            break

                return parts

            sabr_stream, _, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': sabr_error_injector}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)
            # xxx: not recorded as an error in the request history as SabrError is part of normal processing.
            # We rely on assert_media_sequence_in_order to ensure all parts were eventually retrieved and the logs for retry attempts.
            logger.warning.assert_any_call("[sabr] Got error: SABR Protocol Error: SabrError(type='simulated SABR error', action=1, error=None). Retrying (1/10)...")

    class TestGVSFallbackRetries:
        def test_gvs_fallback_after_8_retries(self, logger, client_info):
            # Should fallback to next gvs server after max retries exceeded
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 10))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6',
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # There should be 8 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 8
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Check that the host was switched after 8 retries
            last_error_request = error_requests[-1]
            for following_request in rh.request_history[rh.request_history.index(last_error_request) + 1:]:
                # TODO: this should be rr3, gvs fallback function needs fixing
                assert 'rr1---sn-7654321.googlevideo.com' in following_request.request.url
                assert 'fallback_count=1' in following_request.request.url

            # Check request before fallback
            assert 'rr6---sn-6942067.googlevideo.com' in last_error_request.request.url

            # Should have 8 fallback attempts logged
            for i in range(1, 9):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

            logger.warning.assert_any_call('Falling back to host rr1---sn-7654321.googlevideo.com')

        def test_gvs_fallback_multiple_hosts(self, logger, client_info):
            # Should keep falling back to next gvs server until default max total attempts exceeded
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6',
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be 11 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 11
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'
            # Check that the host was switched after each fallback threshold

            # TODO: fix these hosts, gvs fallback function needs fixing
            retry_request_one = error_requests[8]  # first fallback
            assert 'rr1---sn-7654321.googlevideo.com' in retry_request_one.request.url
            assert 'fallback_count=1' in retry_request_one.request.url
            logger.warning.assert_any_call('Falling back to host rr1---sn-7654321.googlevideo.com')

            retry_request_two = error_requests[9]  # second fallback
            assert 'rr4---sn-7654321.googlevideo.com' in retry_request_two.request.url
            assert 'fallback_count=2' in retry_request_two.request.url
            logger.warning.assert_any_call('Falling back to host rr4---sn-7654321.googlevideo.com')

            retry_request_three = error_requests[10]  # third fallback before giving up
            assert 'rr3---sn-6942067.googlevideo.com' in retry_request_three.request.url
            assert 'fallback_count=3' in retry_request_three.request.url
            logger.warning.assert_any_call('Falling back to host rr3---sn-6942067.googlevideo.com')

        def test_gvs_fallback_threshold_option(self, logger, client_info):
            # Should respect the host_fallback_threshold option for retries before fallback
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 5))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6',
                host_fallback_threshold=3,
            )

            # Should complete successfully
            list(sabr_stream.iter_parts())

            # There should be 3 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 3
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Check that the host was switched after 3 retries
            last_error_request = error_requests[-1]
            for following_request in rh.request_history[rh.request_history.index(last_error_request) + 1:]:
                # TODO: this should be rr3, gvs fallback function needs fixing
                assert 'rr1---sn-7654321.googlevideo.com' in following_request.request.url
                assert 'fallback_count=1' in following_request.request.url

            # Check request before fallback
            assert 'rr6---sn-6942067.googlevideo.com' in last_error_request.request.url

            # Should have 4 fallback attempts logged
            for i in range(1, 4):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

            logger.warning.assert_any_call('Falling back to host rr1---sn-7654321.googlevideo.com')

        def test_gvs_fallback_no_fallback_available(self, logger, client_info):
            # Should not fallback if there are no fallback options available
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com',
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be 11 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 11
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # All should have the same host
            for request in error_requests:
                assert 'rr6---sn-6942067.googlevideo.com' in request.request.url

            assert not any('Falling back to host' in call.args[0] for call in logger.warning.call_args_list)
            assert logger.debug.assert_any_call('No more fallback hosts available')

    class TestStreamProtectionStatusRetries:

        DEFAULT_RETRIES = 5

        def test_sps_retry_on_required(self, logger, client_info):
            # Should retry when StreamProtectionStatus is REQUIRED
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=PoTokenAVProfile(),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            parts = []
            count = 0
            for part in sabr_stream.iter_parts():
                if isinstance(part, PoTokenStatusSabrPart) and part.status != PoTokenStatusSabrPart.PoTokenStatus.OK:
                    count += 1
                    # Supply a simulated po_token on the 4th occurance - to allow one more retry than default
                    if count == self.DEFAULT_RETRIES:
                        sabr_stream.processor.po_token = base64.b64encode(b'simulated_po_token_data')
                parts.append(part)

            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Should have 2 PoTokenStatusSabrPart parts indicating Missing, then the following are all OK
            po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
            assert len(po_token_status_parts) >= self.DEFAULT_RETRIES
            for part in po_token_status_parts[:self.DEFAULT_RETRIES]:
                assert part.status == PoTokenStatusSabrPart.PoTokenStatus.MISSING
            for part in po_token_status_parts[self.DEFAULT_RETRIES:]:
                assert part.status == PoTokenStatusSabrPart.PoTokenStatus.OK

            # Second request should be a retry of the first, so playback time should be the same
            retry_request_vpabr = rh.request_history[1].vpabr
            assert retry_request_vpabr.client_abr_state.player_time_ms == rh.request_history[0].vpabr.client_abr_state.player_time_ms

            # TODO: last retry is warning the po token is invalid, which is not correct
            for i in range(1, self.DEFAULT_RETRIES):
                logger.warning.assert_any_call(f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')

        def test_no_retry_on_pending(self, logger, client_info):
            # Should NOT retry when StreamProtectionStatus is PENDING. Should just continue processing.
            sabr_stream, _, selectors = setup_sabr_stream_av(
                sabr_response_processor=PoTokenAVProfile(),
                client_info=client_info,
                logger=logger,
            )

            sabr_stream.processor.po_token = base64.b64encode(b'pending')
            parts = list(sabr_stream.iter_parts())
            audio_selector, video_selector = selectors

            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
            assert len(po_token_status_parts) >= 1
            for part in po_token_status_parts:
                assert part.status == PoTokenStatusSabrPart.PoTokenStatus.PENDING

        def test_pending_then_required_retry(self, logger, client_info):
            # Test that we can handle going from pending to required to ok with retries
            pending_requests = 2

            sabr_stream, _, selectors = setup_sabr_stream_av(
                sabr_response_processor=PoTokenAVProfile(),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors
            # Start with pending
            sabr_stream.processor.po_token = base64.b64encode(b'pending')

            parts = []
            count = 0
            for part in sabr_stream.iter_parts():
                if isinstance(part, PoTokenStatusSabrPart) and part.status != PoTokenStatusSabrPart.PoTokenStatus.OK:
                    count += 1
                    if count == pending_requests:
                        sabr_stream.processor.po_token = None  # Simulate no token, will get REQUIRED
                    if count == (pending_requests + self.DEFAULT_RETRIES):
                        sabr_stream.processor.po_token = base64.b64encode(b'simulated_po_token_data')
                parts.append(part)

            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Should have 2 PoTokenStatusSabrPart parts indicating Missing, then the following are all OK
            po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
            for part in po_token_status_parts[:pending_requests]:
                assert part.status == PoTokenStatusSabrPart.PoTokenStatus.PENDING
            for part in po_token_status_parts[pending_requests:self.DEFAULT_RETRIES + pending_requests]:
                assert part.status == PoTokenStatusSabrPart.PoTokenStatus.MISSING
            for part in po_token_status_parts[pending_requests + self.DEFAULT_RETRIES:]:
                assert part.status == PoTokenStatusSabrPart.PoTokenStatus.OK

            # TODO: last retry is warning the po token is invalid, which is not correct
            for i in range(1, self.DEFAULT_RETRIES + 1):
                logger.warning.assert_any_call(f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')

        def test_required_exceed_max_retries(self, logger, client_info):
            # Should raise PoTokenError after exceeding max retries when StreamProtectionStatus is REQUIRED
            sabr_stream, _, _ = setup_sabr_stream_av(
                sabr_response_processor=PoTokenAVProfile(),
                client_info=client_info,
                logger=logger,
            )

            sabr_stream.processor.po_token = None  # No token supplied

            with pytest.raises(PoTokenError, match='This stream requires a GVS PO Token to continue'):
                list(sabr_stream.iter_parts())

            # Should log each retry attempt
            for i in range(1, self.DEFAULT_RETRIES + 1):
                logger.warning.assert_any_call(f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')

        def test_pot_retries_options(self, logger, client_info):
            # Should respect the pot_retries option for max retries
            sabr_stream, _, _ = setup_sabr_stream_av(
                sabr_response_processor=PoTokenAVProfile(),
                client_info=client_info,
                logger=logger,
                pot_retries=3,
            )

            sabr_stream.processor.po_token = None  # No token supplied

            with pytest.raises(PoTokenError, match='This stream requires a GVS PO Token to continue'):
                list(sabr_stream.iter_parts())

            # Should log each retry attempt
            for i in range(1, 4):
                logger.warning.assert_any_call(f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/3)...')

        def test_pot_retry_sleep_func(self, logger, client_info):
            # Should call the retry_sleep_func between retries to get the sleep duration
            # For this test, we want to return 0.001 as the sleep
            sleep_mock = MagicMock()
            sleep_mock.side_effect = lambda n: 0.001

            sabr_stream, _, _ = setup_sabr_stream_av(
                sabr_response_processor=PoTokenAVProfile(),
                client_info=client_info,
                logger=logger,
                pot_retries=3,
                retry_sleep_func=sleep_mock,
            )

            sabr_stream.processor.po_token = None  # No token supplied

            with pytest.raises(PoTokenError, match='This stream requires a GVS PO Token to continue'):
                list(sabr_stream.iter_parts())

            # sleep_mock should be called 3 times (for the three retries)
            assert sleep_mock.call_count == 3
            sleep_mock.assert_any_call(n=0)
            sleep_mock.assert_any_call(n=1)
            sleep_mock.assert_any_call(n=2)

            # Check logs for retry attempts
            for i in range(1, 4):
                logger.warning.assert_any_call(f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/3)...')
            # Should log the sleep
            logger.info.assert_any_call('Sleeping 0.00 seconds ...')

        def test_pot_http_retries(self, logger, client_info):
            # Test retry logic when both http retry and pot retry are triggered
            # This can occur when a response contains SPS required but ends on a transport error.
            # Both retries are triggered but http retries take precedence in final error.
            class CustomPoTokenAVProfile(CustomAVProfile, PoTokenAVProfile):
                pass

            # Should retry if a TransportError occurs after we have read all segments in the response and video
            # We can simulate this by adding a informational part at the end that fails to read
            def inject_read_error(parts, vpabr, url, request_number):

                parts.append(UMPPart(
                    part_id=UMPPartId.SNACKBAR_MESSAGE,
                    size=0,
                    data=io.BytesIO(b''),
                ))
                return create_inject_read_error([0, 1, 2, 3], part_id=UMPPartId.SNACKBAR_MESSAGE, occurance=1)(parts, vpabr, url, request_number)

            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=CustomPoTokenAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
                http_retries=2,
                pot_retries=2,
            )

            # TransportError should win
            with pytest.raises(TransportError, match='simulated read error'):
                list(sabr_stream.iter_parts())

            # There should be 3 http error requests recorded
            http_error_requests = [d for d in rh.request_history if isinstance(d.error, TransportError)]
            assert len(http_error_requests) == 3

            for request in http_error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.msg == 'simulated read error'

            # Both retries should be logged with same count
            for i in range(1, 3):
                logger.warning.assert_any_call(f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/2)...')
                logger.warning.assert_any_call(f'[sabr] Got error: simulated read error. Retrying ({i}/2)...')

        def test_pot_http_retries_diff(self, logger, client_info):
            # Test retry logic when both http retry and pot retry are triggered
            # This can occur when a response contains SPS required but ends on a transport error.
            # This test is the same as above, except there are more http retries than pot retries,
            # so the final error should be PoTokenError.

            class CustomPoTokenAVProfile(CustomAVProfile, PoTokenAVProfile):
                pass

            # Should retry if a TransportError occurs after we have read all segments in the response and video
            # We can simulate this by adding a informational part at the end that fails to read
            def inject_read_error(parts, vpabr, url, request_number):

                parts.append(UMPPart(
                    part_id=UMPPartId.SNACKBAR_MESSAGE,
                    size=0,
                    data=io.BytesIO(b''),
                ))
                return create_inject_read_error([0, 1, 2, 3], part_id=UMPPartId.SNACKBAR_MESSAGE, occurance=1)(parts, vpabr, url, request_number)

            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=CustomPoTokenAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
                http_retries=3,
                pot_retries=2,
            )

            # PoTokenError should win
            with pytest.raises(PoTokenError, match='This stream requires a GVS PO Token to continue'):
                list(sabr_stream.iter_parts())

            # There should be 3 http error requests recorded
            http_error_requests = [d for d in rh.request_history if isinstance(d.error, TransportError)]
            assert len(http_error_requests) == 3

            for request in http_error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.msg == 'simulated read error'

            # http retries and pot retries should be logged with same count
            # (note http retries total is 3, pot retries total is 2)
            for i in range(1, 3):
                logger.warning.assert_any_call(f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/2)...')
                logger.warning.assert_any_call(f'[sabr] Got error: simulated read error. Retrying ({i}/3)...')

    class TestAdWait:
        def test_ad_wait(self, logger, client_info):
            # Should send back SabrContextUpdate and wait the specified time in the next request policy
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=AdWaitAVProfile(),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)
            logger.warning.assert_any_call(
                'Received a SABR Context Update. YouTube is likely trying to force ads on the client. This may cause issues with playback.')

            # Second request should be sending the ad wait sabr context update
            ad_wait_request_vpabr = rh.request_history[1].vpabr
            assert len(ad_wait_request_vpabr.streamer_context.sabr_contexts) == 1
            assert ad_wait_request_vpabr.streamer_context.sabr_contexts[0] == SabrContext(
                type=AdWaitAVProfile.CONTEXT_UPDATE_TYPE,
                value=AdWaitAVProfile.CONTEXT_UPDATE_DATA,
            )

            # SabrStream rounds up the wait time to nearest second
            logger.info.assert_any_call('The server is requiring yt-dlp to wait 1 seconds before continuing due to ad enforcement')

            assert AdWaitAVProfile.CONTEXT_UPDATE_TYPE in sabr_stream.processor.sabr_context_updates
            assert sabr_stream.processor.sabr_context_updates[5].value == AdWaitAVProfile.CONTEXT_UPDATE_DATA
            assert sabr_stream.processor.sabr_context_updates[5].scope >= AdWaitAVProfile.CONTEXT_UPDATE_SCOPE
            assert AdWaitAVProfile.CONTEXT_UPDATE_TYPE in sabr_stream.processor.sabr_contexts_to_send

        def test_sending_policy(self, logger, client_info):
            # Should respect the sending policy part to update sabr context state
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=SabrContextSendingPolicyAVProfile(),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            context_update_type = SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_TYPE

            # Request should include the sabr context update
            added_request_vpabr = rh.request_history[SabrContextSendingPolicyAVProfile.REQUEST_ADD_CONTEXT_UPDATE].vpabr
            assert len(added_request_vpabr.streamer_context.sabr_contexts) == 1
            assert added_request_vpabr.streamer_context.sabr_contexts[0] == SabrContext(
                type=context_update_type,
                value=SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_DATA,
            )

            # Later request should remove it as per the policy that was sent by the server
            removed_request_vpabr = rh.request_history[SabrContextSendingPolicyAVProfile.REQUEST_DISABLE_CONTEXT_UPDATE].vpabr
            assert len(removed_request_vpabr.streamer_context.sabr_contexts) == 0

            # Should still be stored in the processor but not sent
            assert context_update_type in sabr_stream.processor.sabr_context_updates
            assert sabr_stream.processor.sabr_context_updates[context_update_type].value == SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_DATA
            assert sabr_stream.processor.sabr_context_updates[context_update_type].scope >= SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_SCOPE

            logger.debug.assert_any_call(f'Server requested to disable SABR Context Update for type {context_update_type}')

            assert len(sabr_stream.processor.sabr_contexts_to_send) == 0

    # TODO: mock time, where time.sleep increments time.time() (but instantly)

    class TestLive:

        LIVE_URL = 'https://example.com/sabr_live?id=123'

        def test_livestream_basic(self, client_info):
            logger = SabrFDLogger(ydl=YoutubeDL({'verbose': True}), prefix='test_live', log_level=SabrLogger.LogLevel.TRACE)
            sabr_stream, _, selectors = setup_sabr_stream_av(
                sabr_response_processor=LiveAVProfile(),
                client_info=client_info,
                logger=logger,
                url=self.LIVE_URL,
                live_segment_target_duration_sec=2,
            )
            audio_selector, video_selector = selectors

            parts = list(sabr_stream.iter_parts())

            assert_media_sequence_in_order(parts, audio_selector, 20)
            assert_media_sequence_in_order(parts, video_selector, 20)
