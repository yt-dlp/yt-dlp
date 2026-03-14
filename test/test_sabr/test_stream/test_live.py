from __future__ import annotations
import io
from unittest.mock import MagicMock
import protobug
import pytest

from yt_dlp.extractor.youtube._proto.innertube import NextRequestPolicy
from test.test_sabr.test_stream.helpers import (
    assert_media_sequence_in_order,
    LiveAVProfile,
    mock_time,
    LIVE_BROADCAST_ID,
    VALID_LIVE_URL,
    setup_sabr_stream_av,
    LiveRetryAVProfile,
)
from yt_dlp.extractor.youtube._proto.videostreaming.reload_player_response import ReloadPlaybackParams
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import (
    StreamStallError,
    BroadcastIdChanged,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart

from yt_dlp.extractor.youtube._streaming.sabr.models import ConsumedRange
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    FormatInitializedSabrPart,
    RefreshPlayerResponseSabrPart,
    MediaSegmentInitSabrPart,
    MediaSeekSabrPart,
)
from yt_dlp.extractor.youtube._streaming.sabr.stream import Heartbeat
from yt_dlp.extractor.youtube._proto.videostreaming import (
    ReloadPlayerResponse,
    VideoPlaybackAbrRequest,
    LiveMetadata,
    SabrSeek,
)
from yt_dlp.networking.exceptions import TransportError, HTTPError


class TestLiveStreamStall:
    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_midway_defaults(self, logger, client_info, post_live):
        # Should raise SabrStreamError if no new segments are received midway through the stream
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 3 requests
            if request_number >= 4:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        with pytest.raises(StreamStallError,
                           match=r'Stream stalled; no activity detected in 6 requests and 10.0 seconds and not near live head.'):
            list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 9; registering stall (count: 6)')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 6

        # No callback registered, and should not try to call heartbeat
        with pytest.raises(AssertionError):
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_midway_max_empty_requests_exceeded(self, logger, client_info, post_live):
        # Should raise SabrStreamError if no new segments are received on the fifth request during live
        # Should exceed the max empty requests of 5
        total_segments = 10
        dvr_segments = 7 if not post_live else 9
        max_empty_requests = 10
        live_end_wait_sec = 5
        segment_target_duration_ms = 2000

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 3 requests
            if request_number >= 4:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            live_end_wait_sec=live_end_wait_sec,
            max_empty_requests=max_empty_requests,
            post_live=post_live,
        )
        assert sabr_stream.live_end_wait_sec == live_end_wait_sec
        with pytest.raises(StreamStallError,
                           match=r'Stream stalled; no activity detected in 10 requests and 18.0 seconds and not near live head.'):
            list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 10)')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 10

        # No callback registered, and should not try to call heartbeat
        with pytest.raises(AssertionError):
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_midway_no_live_metadata_no_heartbeat(self, logger, client_info, post_live):
        # Get a stream stall midway through a live stream with no live metadata,
        # should consider the stream as complete (no error)
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 3 requests
            if request_number >= 4:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
            'omit_live_metadata': True,
        })

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated

        audio_selector, video_selector = selectors
        # Should complete successfully (no error)
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 9; registering stall (count: 6)')
        logger.debug.assert_any_call(
            'No activity detected in 6 requests and 10.0 seconds. '
            'No live metadata available and heartbeat indicates stream may no longer be live; assuming livestream has ended.')

        # We will only get the first few segments
        assert_media_sequence_in_order(parts, audio_selector, 3)
        assert_media_sequence_in_order(parts, video_selector, 3)
        assert sabr_stream._stream_stall_tracker.stalled_requests == 6

        if post_live:
            # Should skip heartbeat check for post-live
            with pytest.raises(AssertionError):
                logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')
        else:
            # Should have tried heartbeat but skipped due to no heartbeat callback provided
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_midway_no_live_metadata_with_heartbeat(self, logger, client_info, post_live):
        # Get a stream stall midway through a live stream with no live metadata,
        # and the heartbeat indicates we are at the end of the stream,
        # should consider the stream as complete (no error)
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 3 requests
            if request_number >= 4:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
            'omit_live_metadata': True,
        })

        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
            heartbeat_callback=heartbeat_callback,
        )
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated

        audio_selector, video_selector = selectors
        # Should complete successfully (no error)
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 9; registering stall (count: 6)')
        logger.debug.assert_any_call(
            'No activity detected in 6 requests and 10.0 seconds. '
            'No live metadata available and heartbeat indicates stream may no longer be live; assuming livestream has ended.')

        # We will only get the first few segments
        assert_media_sequence_in_order(parts, audio_selector, 3)
        assert_media_sequence_in_order(parts, video_selector, 3)
        assert sabr_stream._stream_stall_tracker.stalled_requests == 6

        if post_live:
            # Heartbeat should not have been called for post-live
            heartbeat_callback.assert_not_called()
        else:
            # Heartbeat should have been called at least once
            heartbeat_callback.assert_called()

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_wait_next_request_backoff(self, logger, client_info, post_live):
        # Should backoff max_request_backoff seconds on first empty request
        # If max_request_backoff is greater than live_segment_target_duration_sec
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 3 requests
            if request_number == 4:
                nrp = protobug.dumps(NextRequestPolicy(backoff_time_ms=segment_target_duration_ms * 2))
                part = UMPPart(
                    part_id=UMPPartId.NEXT_REQUEST_POLICY,
                    size=len(nrp),
                    data=io.BytesIO(nrp),
                )
                return [part]
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        logger.debug.assert_any_call('No activity detected in request 4; registering stall (count: 1)')
        logger.debug.assert_any_call('Sleeping for 4 seconds before next request')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_head_consumed_ranges(self, logger, client_info, post_live):
        # Should consider near live head based on consumed ranges and finish stream on stall
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')
        if not post_live:
            logger.trace.assert_any_call(
                'Near live stream head detected based on consumed ranges of active formats: head seq (8) - tolerance (3)')
            logger.debug.assert_any_call(
                'No activity detected in 5 requests and 10.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
            assert sabr_stream._stream_stall_tracker.stalled_requests == 5
            # No callback registered, should check for live
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')
        else:
            logger.trace.assert_any_call(
                'Near live stream head detected based on consumed ranges of active formats: head seq (10) - tolerance (3)')
            logger.debug.assert_any_call(
                'No activity detected in 6 requests and 10.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
            assert sabr_stream._stream_stall_tracker.stalled_requests == 6
            # No callback registered, and should not try to call heartbeat for post-live
            with pytest.raises(AssertionError):
                logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_header_consumed_ranges_missing_izf(self, logger, client_info, post_live):
        # Stream stalled near the head of the stream, but not all format selectors are initialized
        # This can happen at the start of the stream
        total_segments = 2
        segment_target_duration_ms = 2000
        dvr_segments = 1

        class MissingAudioFormatLiveAVProfile(LiveAVProfile):
            def determine_formats(self, vpabr: VideoPlaybackAbrRequest):
                audio_format_id, _ = super().determine_formats(vpabr)
                return audio_format_id, None

        def stall_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 2:
                return []
            return parts

        profile = MissingAudioFormatLiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': stall_func,
        })

        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        with pytest.raises(StreamStallError,
                           match=r'Stream stalled; no activity detected in 6 requests and 10.0 seconds and not near live head.'):
            list(sabr_stream.iter_parts())

        assert len(sabr_stream.processor.initialized_formats) == 1

    @mock_time
    def test_stream_stall_head_consumed_ranges_with_heartbeat(self, logger, client_info):
        # Should consider near live head based on consumed ranges and finish stream on stall
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        # Same as test_stream_stall_head_consumed_ranges but with heartbeat indicating stream is not live,
        # should still finish stream on stall
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')

        logger.trace.assert_any_call(
            'Near live stream head detected based on consumed ranges of active formats: head seq (8) - tolerance (3)')
        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 5

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()

    @mock_time
    def test_stream_stall_head_consumed_ranges_with_heartbeat_premiere(self, logger, client_info):
        # Should consider near live head based on consumed ranges and finish stream on stall
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        # Same as test_stream_stall_head_consumed_ranges but with heartbeat indicating stream is not live.
        # Sanity check case for premieres: The broadcast id in the url is 0, whereas it doesn't exist in the heartbeat
        # should still finish stream on stall
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=None, video_id='video_id')

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url='https://live.googlevideo.com/sabr_live?id=test.0&source=yt_live_broadcast&sabr=1',
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')

        logger.trace.assert_any_call(
            'Near live stream head detected based on consumed ranges of active formats: head seq (8) - tolerance (3)')
        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 5

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()

    @mock_time
    def test_stream_stall_head_consumed_ranges_with_heartbeat_error(self, logger, client_info):
        # Should consider near live head based on consumed ranges and finish stream on stall
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        # Same as test_stream_stall_head_consumed_ranges but with heartbeat raising an error (should be ignored)
        # should still finish stream on stall
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        heartbeat_callback = MagicMock()
        # raise an error on callback
        heartbeat_callback.side_effect = Exception('heartbeat error')

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')

        logger.trace.assert_any_call(
            'Near live stream head detected based on consumed ranges of active formats: head seq (8) - tolerance (3)')
        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 5

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()
        logger.warning.assert_any_call(
            'Error occurred while calling heartbeat callback, skipping heartbeat check: heartbeat error')

    @mock_time
    def test_stream_stall_head_consumed_ranges_with_heartbeat_invalid_response(self, logger, client_info):
        # Should consider near live head based on consumed ranges and finish stream on stall
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        # Same as test_stream_stall_head_consumed_ranges but with heartbeat returning an invalid response
        # should still finish stream on stall
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        heartbeat_callback = MagicMock()
        # bad response from callback
        heartbeat_callback.return_value = 'invalid response'

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')

        logger.trace.assert_any_call(
            'Near live stream head detected based on consumed ranges of active formats: head seq (8) - tolerance (3)')
        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 5

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()
        logger.warning.assert_any_call('Invalid heartbeat response received, skipping heartbeat check')

    @mock_time
    def test_stream_stall_head_consumed_ranges_with_heartbeat_no_response(self, logger, client_info):
        # Should consider near live head based on consumed ranges and finish stream on stall
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        # Same as test_stream_stall_head_consumed_ranges but with heartbeat returning no response
        # should still finish stream on stall
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        heartbeat_callback = MagicMock()
        # no response from callback
        heartbeat_callback.return_value = None

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')

        logger.trace.assert_any_call(
            'Near live stream head detected based on consumed ranges of active formats: head seq (8) - tolerance (3)')
        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 5

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()
        logger.debug.assert_any_call('Heartbeat callback returned no response, skipping heartbeat check')

    @mock_time
    def test_stream_stall_head_consumed_ranges_with_heartbeat_broadcast_id_change(self, logger, client_info):
        # Should consider near live head based on consumed ranges and finish stream on stall
        # This should calculate a default live_end_wait_sec of 10 seconds (as segment target duration * max_empty_requests = 2s * 3 = 6s))
        # Same as test_stream_stall_head_consumed_ranges but with heartbeat returning a different broadcast_id
        # This could happen if the broadcast ended and a new one started with the same video_id.
        # The BroadcastIdChange error should be raised in this case
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=True, broadcast_id='2', video_id='video_id')

        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated

        with pytest.raises(
            BroadcastIdChanged,
            match=rf'Broadcast ID changed from {LIVE_BROADCAST_ID} to 2. The download will need to be restarted.',
        ):
            list(sabr_stream.iter_parts())

        heartbeat_callback.assert_called()

    @mock_time
    def test_stream_stall_head_consumed_ranges_chain(self, logger, client_info):
        # Should consider stream as complete if near live head based on consumed ranges chain
        # player_time_ms / current consumed ranges do not indicate near live head, but consumed ranges chain does

        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        # So we know the exact number of stalls
        max_empty_requests = 10
        live_end_wait_sec = 5

        # First pass to collect segment information to generate consumed ranges
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            enable_audio=False,
            max_empty_requests=max_empty_requests,
            live_end_wait_sec=live_end_wait_sec,
        )
        iter_parts = sabr_stream.iter_parts()
        format_init_part = next(iter_parts)
        assert isinstance(format_init_part, FormatInitializedSabrPart)
        # Get all the media init parts
        media_init_parts = [part for part in iter_parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts) == total_segments

        #  Now set up buffered ranges to skip some segments
        consumed_ranges = [
            # Mark all but the first 2 segments as consumed
            # note: no init parts with live
            ConsumedRange(
                start_sequence_number=media_init_parts[2].sequence_number,
                end_sequence_number=media_init_parts[-1].sequence_number,
                start_time_ms=media_init_parts[2].start_time_ms,
                duration_ms=sum(part.duration_ms for part in media_init_parts[2:-1]),
            ),
        ]

        # Reset the sabr stream with custom consumed ranges chain
        # We still stall the stream when the player time is within the already consumed ranges
        stall_count = 0

        def no_new_segments_func(parts, vpabr, url, request_number):
            nonlocal stall_count
            # Stop returning new segments after 8 requests
            if vpabr.client_abr_state.player_time_ms >= consumed_ranges[0].start_time_ms:
                stall_count += 1
                # Send back RELOAD_PLAYER_RESPONSE parts so we can update consumed ranges
                rpr = protobug.dumps(ReloadPlayerResponse(
                    reload_playback_params=ReloadPlaybackParams(token='test token'),
                ))

                return [
                    UMPPart(
                        part_id=UMPPartId.RELOAD_PLAYER_RESPONSE,
                        size=len(rpr),
                        data=io.BytesIO(rpr),
                    ),
                ]
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            enable_audio=False,
            max_empty_requests=max_empty_requests,
            live_end_wait_sec=live_end_wait_sec,
        )

        # Stream until stall_count reaches 2, then we'll add the consumed ranges.
        # On that request, it should detect it is near the live head based on the consumed
        # range chain and finish, instead of making another request.

        parts = []
        for part in sabr_stream.iter_parts():
            if stall_count == max_empty_requests and isinstance(part, RefreshPlayerResponseSabrPart):
                sabr_stream.processor.initialized_formats[
                    str(format_init_part.format_id)].consumed_ranges = consumed_ranges
            parts.append(part)

        # Expect that the only media init parts we get is first 2 segments
        media_init_parts_received = [part for part in parts if isinstance(part, MediaSegmentInitSabrPart)]
        assert len(media_init_parts_received) == 3
        assert media_init_parts_received[0].sequence_number == 1
        assert media_init_parts_received[2].sequence_number == 3

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 10)')
        logger.trace.assert_any_call(
            'Near live stream head detected based on consumed ranges of active formats: head seq (10) - tolerance (3)')
        logger.debug.assert_any_call(
            'No activity detected in 10 requests and 18.0 seconds. Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 10

        # Last request player_time_ms should be around the start of the added consumed range
        # Ensure the stream ended due to near live head detection on the consumed range chain,
        # not because the player_time_ms was anywhere near the head.
        assert rh.request_history[-1].vpabr.client_abr_state.player_time_ms < consumed_ranges[
            0].start_time_ms + segment_target_duration_ms

        # No callback registered, should check for live
        logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_head_consumed_ranges_single_format(self, logger, client_info, post_live):
        # Should consider near live head based on consumed ranges of single active format and finish stream on stall
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            enable_audio=False,
            post_live=post_live,
        )
        _, video_selector = selectors

        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        parts = list(sabr_stream.iter_parts())

        if not post_live:
            logger.trace.assert_any_call(
                'Near live stream head detected based on consumed ranges of active formats: head seq (8) - tolerance (3)')
            logger.debug.assert_any_call(
                'No activity detected in 5 requests and 10.0 seconds. '
                'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
            assert sabr_stream._stream_stall_tracker.stalled_requests == 5
        else:
            logger.trace.assert_any_call(
                'Near live stream head detected based on consumed ranges of active formats: head seq (10) - tolerance (3)')
            logger.debug.assert_any_call(
                'No activity detected in 6 requests and 10.0 seconds. '
                'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
            assert sabr_stream._stream_stall_tracker.stalled_requests == 6

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_head_near_head_time(self, logger, client_info, post_live):
        # Should consider the stream as finished if near the live head based on player time
        # Case where the consumed ranges are not sufficient to determine near live head

        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9
        live_head_tolerance_sec = 5

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        # We can skip the check on live head segment by making the server not return it
        class RemoveLiveHeadSegmentNumberLiveProfile(LiveAVProfile):
            def generate_live_metadata(self, current_segment: int) -> LiveMetadata:
                lm = super().generate_live_metadata(current_segment)
                lm.head_sequence_number = None
                return lm

        profile = RemoveLiveHeadSegmentNumberLiveProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        sabr_stream.live_head_tolerance_sec = live_head_tolerance_sec
        parts = list(sabr_stream.iter_parts())

        if not post_live:
            logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')
            logger.trace.assert_any_call(
                'Near or at live stream head detected based on player time and head sequence end time with tolerance (ms): 14000 >= 15900 - 6000')
            logger.debug.assert_any_call(
                'No activity detected in 5 requests and 10.0 seconds. '
                'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
            assert sabr_stream._stream_stall_tracker.stalled_requests == 5
            # No callback registered, should check for live
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

        else:
            logger.debug.assert_any_call('No activity detected in request 14; registering stall (count: 6)')
            logger.trace.assert_any_call(
                'Near or at live stream head detected based on player time and head sequence end time with tolerance (ms): 15900 >= 19900 - 6000')
            logger.debug.assert_any_call(
                'No activity detected in 6 requests and 10.0 seconds. '
                'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
            assert sabr_stream._stream_stall_tracker.stalled_requests == 6
            # No callback registered, and should not try to call heartbeat for post-live
            with pytest.raises(AssertionError):
                logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

    @mock_time
    def test_stream_stall_head_near_head_time_with_heartbeat(self, logger, client_info):
        # Should consider the stream as finished if near the live head based on player time
        # Case where the consumed ranges are not sufficient to determine near live head
        # Same as test_stream_stall_head_near_head_time but with heartbeat indicating stream is not live,
        # should still finish stream on stall

        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7
        live_head_tolerance_sec = 5

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 8 requests
            if request_number >= 9:
                return []
            return parts

        # We can skip the check on live head segment by making the server not return it
        class RemoveLiveHeadSegmentNumberLiveProfile(LiveAVProfile):
            def generate_live_metadata(self, current_segment: int) -> LiveMetadata:
                lm = super().generate_live_metadata(current_segment)
                lm.head_sequence_number = None
                return lm

        profile = RemoveLiveHeadSegmentNumberLiveProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })
        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.live_end_wait_sec == 10.0  # Default calculated
        sabr_stream.live_head_tolerance_sec = live_head_tolerance_sec
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 13; registering stall (count: 5)')
        logger.trace.assert_any_call(
            'Near or at live stream head detected based on player time and head sequence end time with tolerance (ms): 14000 >= 15900 - 6000')
        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. '
            'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')
        assert sabr_stream._stream_stall_tracker.stalled_requests == 5
        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()

        # We will get all but the last 2 segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 2,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 2,
                                       check_segment_total_segments=False)

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_stream_stall_no_live_metadata_head_details(self, logger, client_info, post_live):
        # If get a stream through a live stream with no live metadata head details - should fail
        # TODO: should this gracefully exit instead similar to having no live_metadata?
        # TODO: should we consider falling back to max_seekable?
        # TODO: this is an unlikely case, as live streams either have live_metadata with all fields or no live_metadata
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 7 if not post_live else 9

        def no_new_segments_func(parts, vpabr, url, request_number):
            # Stop returning new segments after 3 requests
            if request_number >= 4:
                return []
            return parts

        class NoLiveHeadDetailsLiveProfile(LiveAVProfile):
            def generate_live_metadata(self, current_segment: int) -> LiveMetadata:
                lm = super().generate_live_metadata(current_segment)
                lm.head_sequence_number = None
                lm.head_sequence_time_ms = None
                return lm

        profile = NoLiveHeadDetailsLiveProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': no_new_segments_func,
        })

        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )

        with pytest.raises(StreamStallError,
                           match=r'Stream stalled; no activity detected in 6 requests and 10.0 seconds and not near live head.'):
            list(sabr_stream.iter_parts())

        assert sabr_stream._stream_stall_tracker.stalled_requests == 6

        # Should not have tried to check heartbeat callback
        with pytest.raises(AssertionError):
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

    @mock_time
    def test_stream_stall_at_head_sequence_number(self, logger, client_info):
        # If we reach the live head sequence number, should stall and should consider stream complete
        # note: does not apply for post_live, who should detect immediate end of stream
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())

        logger.debug.assert_any_call('No activity detected in request 15; registering stall (count: 5)')
        logger.trace.assert_any_call(
            'Near live stream head detected based on consumed ranges of active formats: head seq (10) - tolerance (3)')
        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. '
            'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')

        assert sabr_stream._stream_stall_tracker.stalled_requests == 5
        # We will get all segments in this example
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Should have tried heartbeat but skipped due to no heartbeat callback provided
        logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_sabr_seek_before_head_stall(self, logger, client_info, post_live):
        # Cannot get the head segment, and the server seeks the client
        # just after the n-1 segment (as to not be within the consumed range)
        # NOTE: player_time_ms gets reset back to the max_seekable_time_ms, which is usually a little before the head
        #  For these tests, max_seekable_time_ms is the same as the head.
        # This is a regression test for a case that used to cause issues when an old implementation.
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        class DisallowLastSegmentprofile(LiveAVProfile):
            def next_segment(self, buffered_segments: set[int], player_time_ms: int) -> int | None:
                # If next_segment is segment 10, do not return it
                next_seg = super().next_segment(buffered_segments, player_time_ms)
                if next_seg == 10:
                    return None
                return next_seg

            def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[
                    UMPPart | Exception]:
                parts = super().get_parts(vpabr, url, request_number)
                # if no media parts, seek to end just before head segment
                if not any(part.part_id == UMPPartId.MEDIA_HEADER for part in parts):
                    sabr_seek = protobug.dumps(SabrSeek(
                        seek_time_ticks=self.live_head_segment_start_ms() + 1000,
                        timescale=1000,
                    ))
                    parts.append(UMPPart(
                        part_id=UMPPartId.SABR_SEEK,
                        size=len(sabr_seek),
                        data=io.BytesIO(sabr_seek),
                    ))
                return parts

        profile = DisallowLastSegmentprofile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })

        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )

        parts = list(sabr_stream.iter_parts())
        audio_selector, video_selector = selectors
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1,
                                       check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1,
                                       check_segment_total_segments=False)

        # Check we got seeks
        assert any(isinstance(part, MediaSeekSabrPart) for part in parts)

        if not post_live:
            # live will get reset to max_seekable_time_ms, which should be near or in the latest consumed range
            logger.trace.assert_any_call(
                'Near live stream head detected based on consumed ranges of active formats: head seq (10) - tolerance (3)')
        else:
            # post-live does not get reset to max_seekable_time_ms, so should stay where it was seeked to
            logger.trace.assert_any_call(
                'Near or at live stream head detected based on player time and head sequence end time with tolerance (ms): 19000 >= 19900 - 6000')
        logger.debug.assert_any_call(
            'No activity detected in 6 requests and 10.0 seconds. '
            'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')

    @mock_time
    def test_live_stall_heartbeat_allows_resume(self, logger, client_info):
        # Simulate a live stream that stalls long enough to exceed the
        # configured max_empty_requests/time at the live head, but the heartbeat reports the
        # stream is still up. The server starts returning segments after that.
        total_segments = 6
        segment_target_duration_ms = 2000
        max_empty_requests = 3
        dvr_segments = 1  # so always at live head

        # After this many requests the server will resume sending segments.
        start_empty_after_request = 1
        resume_after_request = 10

        assert resume_after_request - start_empty_after_request > max_empty_requests

        # Heartbeat reporting stream is still live
        heartbeat_callback = MagicMock()

        def stall_then_resume(parts, vpabr, url, request_number):
            # Return no parts (stall) for the first N requests, then delegate to real profile.
            # Allow first request to go through
            if start_empty_after_request < request_number <= resume_after_request:
                heartbeat_callback.return_value = Heartbeat(
                    is_live=True, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')
                return []
            # Need to set to not live so stream does end
            heartbeat_callback.return_value = Heartbeat(
                is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': stall_then_resume,
        })

        # Provide a heartbeat callback that always reports the stream is alive.
        # Pass it through setup options so SabrStream uses it during stall detection.
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            max_empty_requests=max_empty_requests,
            heartbeat_callback=heartbeat_callback,
        )

        parts = list(sabr_stream.iter_parts())

        audio_selector, video_selector = selectors
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Ensure requests were made during the stall and after resume.
        assert len(rh.request_history) > resume_after_request
        # The stalled requests at the start should have empty parts
        for r in rh.request_history[start_empty_after_request:resume_after_request]:
            assert r.parts == []
        # A later request should contain parts
        assert any(r.parts for r in rh.request_history[resume_after_request:])
        heartbeat_callback.assert_called()

        logger.debug.assert_any_call(
            'No activity detected in 9 requests and 10.0 seconds. '
            'Near live stream head but heartbeat indicates stream is still live; continuing to wait for segments.')

        logger.debug.assert_any_call(
            'No activity detected in 5 requests and 10.0 seconds. '
            'Near live stream head and heartbeat indicates stream may no longer be live; assuming livestream has ended.')

    @mock_time
    def test_live_stall_no_live_metadata_heartbeat_allows_resume(self, logger, client_info):
        # Simulate a live stream with no live metadata that stalls long enough to exceed the
        # configured max_empty_requests/time, but the heartbeat reports the stream is still up.
        # The server starts returning segments after that.
        total_segments = 6
        segment_target_duration_ms = 2000
        max_empty_requests = 3
        dvr_segments = 1  # so always at live head

        # After this many requests the server will resume sending segments.
        start_empty_after_request = 1
        resume_after_request = 10

        assert resume_after_request - start_empty_after_request > max_empty_requests

        # Heartbeat reporting stream is still live
        heartbeat_callback = MagicMock()

        def stall_then_resume(parts, vpabr, url, request_number):
            # Return no parts (stall) for the first N requests, then delegate to real profile.
            # Allow first request to go through
            if start_empty_after_request < request_number <= resume_after_request:
                heartbeat_callback.return_value = Heartbeat(
                    is_live=True, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')
                return []
            # Need to set to not live so stream does end
            heartbeat_callback.return_value = Heartbeat(
                is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': stall_then_resume,
            'omit_live_metadata': True,
        })

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            max_empty_requests=max_empty_requests,
            heartbeat_callback=heartbeat_callback,
        )

        parts = list(sabr_stream.iter_parts())

        audio_selector, video_selector = selectors
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Ensure requests were made during the stall and after resume.
        assert len(rh.request_history) > resume_after_request
        # The stalled requests at the start should have empty parts
        for r in rh.request_history[start_empty_after_request:resume_after_request]:
            assert r.parts == []
        # A later request should contain parts
        assert any(r.parts for r in rh.request_history[resume_after_request:])

        heartbeat_callback.assert_called()
        logger.debug.assert_any_call(
            'No activity detected in 9 requests and 10.0 seconds. '
            'No live metadata available but heartbeat indicates stream is still live; continuing to wait for segments.')

        logger.debug.assert_any_call(
            'No activity detected in 6 requests and 10.0 seconds. '
            'No live metadata available and heartbeat indicates stream may no longer be live; assuming livestream has ended.')


class TestPostLiveEnd:
    @mock_time
    def test_post_live_stream_end(self, logger, client_info):
        # Should consider post live stream as finished as soon as reach live head segment
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=True,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Should be no waiting for post_live
        assert rh.request_history[-1].time == 0.0
        logger.trace.assert_any_call(
            'All enabled formats have reached their last expected segment at player time 19900 ms, assuming end of vod.')

        # Should not try to check heartbeat for post-live end detection
        with pytest.raises(AssertionError):
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')

    @mock_time
    def test_post_live_stream_end_heartbeat_check(self, logger, client_info):
        # Should consider post live stream as finished as soon as reach live head segment
        # Should not check the heartbeat for post-live end
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })
        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=True,
            heartbeat_callback=heartbeat_callback,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Should be no waiting for post_live
        assert rh.request_history[-1].time == 0.0
        logger.trace.assert_any_call(
            'All enabled formats have reached their last expected segment at player time 19900 ms, assuming end of vod.')

        # Should not try to check heartbeat for post-live end detection
        heartbeat_callback.assert_not_called()

    @mock_time
    def test_post_live_stream_end_player_time(self, logger, client_info):
        # Test post live stream end based on player time exceeding head end time
        # We can simulate this by remove head segment from the live_metadata
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        # We can skip the check on live head segment by making the server not return it
        class RemoveLiveHeadSegmentNumberLiveProfile(LiveAVProfile):
            def generate_live_metadata(self, current_segment: int) -> LiveMetadata:
                lm = super().generate_live_metadata(current_segment)
                lm.head_sequence_number = None
                return lm

        profile = RemoveLiveHeadSegmentNumberLiveProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=True,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # should not have any stalls as should finish immediately based on player time
        assert sabr_stream._stream_stall_tracker.stalled_requests == 0

        # Should be no waiting for post_live
        assert rh.request_history[-1].time == 0.0

        live_end_tolerance = sabr_stream.processor.live_segment_target_duration_tolerance_ms
        assert live_end_tolerance == 100  # default
        estimated_end_time = (total_segments * segment_target_duration_ms) - live_end_tolerance
        # Should NOT use any tolerance when checking for immediate post live end based on player time
        logger.trace.assert_any_call(
            'Near or at live stream head detected based on player time '
            f'and head sequence end time with tolerance (ms): {estimated_end_time} >= {estimated_end_time} - 0')

        # Should not try to check heartbeat for post-live end detection
        with pytest.raises(AssertionError):
            logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')


class TestLive:

    @mock_time
    def test_livestream_max_seekable_time(self, logger, client_info):
        # should not request player_time_ms any higher than the max seekable time
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 0
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'max_seekable_before_head': True,
        })

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # For each request, compare the live metadata max seekable time
        #  with the requested player time ms - should be less than or equal to the max seekable time
        for request in rh.request_history:
            live_metadata = None
            for part in request.parts:
                if part.part_id == UMPPartId.LIVE_METADATA:
                    if hasattr(part.data, 'seek'):
                        part.data.seek(0)
                    live_metadata = protobug.loads(part.data.read(), LiveMetadata)
            max_seekable_time_ms = (
                live_metadata.max_seekable_time_ticks * 1000) // live_metadata.max_seekable_timescale
            player_time_ms = request.vpabr.client_abr_state.player_time_ms
            assert player_time_ms <= max_seekable_time_ms, f'Requested player time {player_time_ms} ms exceeds max seekable time {max_seekable_time_ms} ms in live metadata'

        logger.trace.assert_any_call('Setting player time to max seekable time ms: 16000ms (-1900ms)')

    @mock_time
    def test_livestream_no_dvr_wait_time(self, logger, client_info):
        total_segments = 3
        segment_target_duration_ms = 3000
        dvr_segments = 0
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Should wait between every request
        for i in range(1, len(rh.request_history)):
            prev_request = rh.request_history[i - 1]
            curr_request = rh.request_history[i]
            time_diff = int(curr_request.time - prev_request.time)
            assert time_diff == segment_target_duration_ms // 1000

        logger.debug.assert_any_call(f'Sleeping for {segment_target_duration_ms // 1000} seconds before next request')

    @mock_time
    def test_livestream_no_dvr_next_request_backoff_wait_time(self, logger, client_info):
        # Same as test_livestream_no_dvr_wait_time, but should use the max_request_backoff_sec
        # as the wait time if it is more than the segment target duration
        total_segments = 3
        segment_target_duration_ms = 2000
        dvr_segments = 0
        backoff_time_ms = segment_target_duration_ms + 1000

        def next_request_policy(parts, vpabr, url, request_number):
            nrp = protobug.dumps(NextRequestPolicy(
                backoff_time_ms=backoff_time_ms,
            ))
            return [*parts, UMPPart(part_id=UMPPartId.NEXT_REQUEST_POLICY, size=len(nrp), data=io.BytesIO(nrp))]

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': next_request_policy,

        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Should wait the backoff time between every request
        for i in range(1, len(rh.request_history)):
            prev_request = rh.request_history[i - 1]
            curr_request = rh.request_history[i]
            time_diff = int(curr_request.time - prev_request.time)
            assert time_diff == backoff_time_ms // 1000

        logger.debug.assert_any_call(f'Sleeping for {backoff_time_ms // 1000} seconds before next request')

    @mock_time
    def test_livestream_dvr_wait_time(self, logger, client_info):
        total_segments = 6
        segment_target_duration_ms = 2000
        dvr_segments = 3
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # Should get the first 4 segments without waiting (first live segment is immediately available)
        dvr_requests = rh.request_history[:4]
        for i in range(1, len(dvr_requests)):
            prev_request = dvr_requests[i - 1]
            curr_request = dvr_requests[i]
            time_diff = int(curr_request.time - prev_request.time)
            assert time_diff == 0, f'Expected no wait between DVR segment requests, got {time_diff} seconds (request {i} and {i - 1})'

            # Check buffered ranges to ensure ends on the expected segment
            vpabr = curr_request.vpabr
            for br in vpabr.buffered_ranges:
                assert br.end_segment_index == i, f'Expected buffered range to end on segment {i}, got {br.end_segment_index}'

        # Should wait between subsequent segments (or receive no segments)
        for i in range(4, len(rh.request_history)):
            prev_request = rh.request_history[i - 1]
            curr_request = rh.request_history[i]
            time_diff = int(curr_request.time - prev_request.time)
            assert time_diff == segment_target_duration_ms // 1000

        logger.debug.assert_any_call(f'Sleeping for {segment_target_duration_ms // 1000} seconds before next request')

    @mock_time
    def test_livestream_manual_seek_min(self, logger, client_info):
        # If a livestream min seekable offset is > 0, should seek to that offset on start
        # NOTE: no SABR_SEEK is used in this test
        total_segments = 3
        segment_target_duration_ms = 3000
        dvr_segments = 0
        segment_start_number = 5  # segment counting starts from 5
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'start_segment_number': segment_start_number,
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        assert_media_sequence_in_order(parts, audio_selector, total_segments,
                                       start_sequence_number=segment_start_number)
        assert_media_sequence_in_order(parts, video_selector, total_segments,
                                       start_sequence_number=segment_start_number)

        # First request: should start from 0
        first_request_vpabr = rh.request_history[0].vpabr
        assert first_request_vpabr.client_abr_state.player_time_ms == 0
        # Second request: should seek to min seekable offset specified in live_metadata
        second_request_vpabr = rh.request_history[1].vpabr
        expected_seek_time_ms = segment_target_duration_ms * (segment_start_number - 1)
        assert second_request_vpabr.client_abr_state.player_time_ms == expected_seek_time_ms

        logger.debug.assert_any_call('Player time 0 is less than min seekable time 12000, simulating server seek')

    @mock_time
    def test_livestream_manual_seek_max(self, logger, client_info):
        # If a livestream max seekable offset is less than initial player time ms, should seek back to that
        # NOTE: no SABR_SEEK is used in this test
        total_segments = 5
        segment_target_duration_ms = 3000
        dvr_segments = 4
        start_sequence_number = 1
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'start_segment_number': start_sequence_number,
            'max_seekable_before_head': True,
        })
        initial_live_head_segment_start_ms = profile.live_head_segment_start_ms()
        start_time_ms = initial_live_head_segment_start_ms + 10000
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            start_time_ms=start_time_ms,  # start 10s past live head
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        # test server should send segments 2 before the head segment (max seekable is -1, then -1 before that due to buffer logic)
        assert_media_sequence_in_order(parts, audio_selector, 3, start_sequence_number=profile.live_head_segment() - 2)
        assert_media_sequence_in_order(parts, video_selector, 3, start_sequence_number=profile.live_head_segment() - 2)

        # First request: should start from 0
        first_request_vpabr = rh.request_history[0].vpabr
        assert first_request_vpabr.client_abr_state.player_time_ms == start_time_ms
        # Second request: Should seek back to max_seekable_time_ms specified in live_metadata
        second_request_vpabr = rh.request_history[1].vpabr
        assert second_request_vpabr.client_abr_state.player_time_ms == profile.max_seekable_time_ms

        logger.debug.assert_any_call(
            'Skipping player time increment; one or more initialized formats is missing a consumed range for current player time')
        logger.trace.assert_any_call(
            f'Setting player time to max seekable time ms: {profile.max_seekable_time_ms}ms (-5900ms)')

    @mock_time
    def test_skip_player_time_increment_if_seeking(self, logger, client_info):
        # if one format is marked as seeking at the end of the response, then do not increment the player time.
        # To simulate:
        # 1. Init both formats
        # 2. Provide first segment of one format
        # 3. SabrSeek
        # 4. End response without providing more data

        total_segments = 3
        segment_target_duration_ms = 2000
        dvr_segments = 2

        seek_ms = segment_target_duration_ms // 2

        def seeking_format_func(parts, vpabr, url, request_number):
            if request_number == 1:
                # Include all parts until the first MEDIA_END
                parts = parts[:parts.index(next(p for p in parts if p.part_id == UMPPartId.MEDIA_END)) + 1]

                # Add SABR_SEEK after the MEDIA_END
                sabr_seek = protobug.dumps(SabrSeek(
                    seek_time_ticks=seek_ms,
                    timescale=1000,
                ))
                parts.append(UMPPart(
                    part_id=UMPPartId.SABR_SEEK,
                    size=len(sabr_seek),
                    data=io.BytesIO(sabr_seek),
                ))
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': seeking_format_func,
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # First request: should start from 0
        first_request_vpabr = rh.request_history[0].vpabr
        assert first_request_vpabr.client_abr_state.player_time_ms == 0
        # Second request: should seek to seek_ms, not to what the first format is set to.
        second_request_vpabr = rh.request_history[1].vpabr
        assert second_request_vpabr.client_abr_state.player_time_ms == seek_ms

        logger.debug.assert_any_call('Seeking to 1000ms')
        logger.debug.assert_any_call('Skipping player time increment; one or more initialized formats are currently seeking')

    @mock_time
    def test_create_stats_str_live(self, logger, client_info):
        # Simple test of the stats string created for live streams
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
        })
        sabr_stream, _, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        stats_str = sabr_stream.create_stats_str()
        expected_stats_str = (
            'v:unknown c:WEB t:18000 h:live exp:n/a rn:15 sr:5 act:N pot:N sps:n/a'
            ' live 2s bid:1 hs:10 hst:18000 mxt:18000 mnt:0'
            ' if:[140(10), 248(10)] cr:[140:1-10 (0-19900), 248:1-10 (0-19900)]'
        )
        assert stats_str == expected_stats_str

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_sabr_seek(self, logger, client_info, post_live):
        # Should follow SABR_SEEK for live/post_live streams
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        seek_ms = segment_target_duration_ms * 4

        def seeking_format_func(parts, vpabr, url, request_number):
            if request_number == 1:
                sabr_seek = protobug.dumps(SabrSeek(
                    seek_time_ticks=seek_ms,
                    timescale=1000,
                ))
                parts.append(UMPPart(
                    part_id=UMPPartId.SABR_SEEK,
                    size=len(sabr_seek),
                    data=io.BytesIO(sabr_seek),
                ))
            return parts
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': seeking_format_func,
        })
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            post_live=post_live,
        )
        list(sabr_stream.iter_parts())

        assert len(rh.request_history) > 1
        first_request_vpabr = rh.request_history[0].vpabr
        assert first_request_vpabr.client_abr_state.player_time_ms == 0
        second_request_vpabr = rh.request_history[1].vpabr
        assert second_request_vpabr.client_abr_state.player_time_ms == seek_ms
        logger.debug.assert_any_call(f'Seeking to {seek_ms}ms')


class TestLiveEndErrorRetriesExhausted:
    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_transport_error_at_end_consumed(self, logger, client_info, post_live):
        # Should mark the stream as consumed and safely exit when:
        # - On last retry for transport errors
        # - near the head of the stream
        # - heartbeat strictly indicates stream is no longer live
        # - all formats have been initialized
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'transport',
            'rn': list(range(10, 30)),
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
            post_live=post_live,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Callback should have been called only for live streams
        if not post_live:
            heartbeat_callback.assert_called()
        else:
            heartbeat_callback.assert_not_called()

        logger.debug.assert_any_call(
            'Retry attempts exceeded, but near the live stream head and live stream has ended. '
            'Assuming reached end of stream.')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_http_error_at_end_consumed(self, logger, client_info, post_live):
        # Should mark the stream as consumed and safely exit when:
        # - On last retry for http errors
        # - near the head of the stream
        # - heartbeat strictly indicates stream is no longer live
        # - all formats have been initialized
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'http',
            'rn': list(range(10, 30)),
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
            post_live=post_live,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, HTTPError)
            assert request.error.status == 500

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: HTTP Error 500: Internal Server Error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Callback should have been called only for live streams
        if not post_live:
            heartbeat_callback.assert_called()
        else:
            heartbeat_callback.assert_not_called()

        logger.debug.assert_any_call(
            'Retry attempts exceeded, but near the live stream head and live stream has ended. '
            'Assuming reached end of stream.')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_transport_error_at_end_consumed_custom_retry(self, logger, client_info, post_live):
        # Should mark the stream as consumed and safely exit when:
        # - On last retry for transport errors
        # - near the head of the stream
        # - heartbeat strictly indicates stream is no longer live
        # - all formats have been initialized
        # With a custom http_retries value

        http_retries = 4
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'transport',
            'rn': list(range(10, 30)),
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
            post_live=post_live,
            http_retries=http_retries,
        )
        assert sabr_stream.http_retries == http_retries
        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == http_retries + 1
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, http_retries):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/{http_retries})...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Callback should have been called only for live streams
        if not post_live:
            heartbeat_callback.assert_called()
        else:
            heartbeat_callback.assert_not_called()

        logger.debug.assert_any_call(
            'Retry attempts exceeded, but near the live stream head and live stream has ended. '
            'Assuming reached end of stream.')

    @mock_time
    def test_error_at_end_no_heartbeat_configured(self, logger, client_info):
        # Should NOT mark the stream as consumed and safely exit when:
        # - On last retry of transport error
        # - near the head of the stream
        # - heartbeat IS NOT CONFIGURED
        # - all formats have been initialized
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'transport',
            'rn': list(range(10, 30)),
        })
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=None,  # no heartbeat configured
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = []

        with pytest.raises(TransportError, match='simulated transport error'):
            for part in sabr_stream.iter_parts():
                parts.append(part)

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        logger.debug.assert_any_call('No heartbeat callback provided, skipping heartbeat check')
        logger.debug.assert_any_call('Heartbeat does not indicate stream has finished; not marking stream as consumed on last retry')

    @mock_time
    def test_error_at_end_heartbeat_no_response(self, logger, client_info):
        # Should NOT mark the stream as consumed and safely exit when:
        # - On last retry of transport error
        # - near the head of the stream
        # - heartbeat RETURNS NO RESPONSE
        # - all formats have been initialized
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'transport',
            'rn': list(range(10, 30)),
        })
        heartbeat_callback = MagicMock()
        # no response from callback
        heartbeat_callback.return_value = None
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = []

        with pytest.raises(TransportError, match='simulated transport error'):
            for part in sabr_stream.iter_parts():
                parts.append(part)

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()
        logger.debug.assert_any_call('Heartbeat callback returned no response, skipping heartbeat check')
        logger.debug.assert_any_call('Heartbeat does not indicate stream has finished; not marking stream as consumed on last retry')

    @mock_time
    def test_error_at_end_heartbeat_error(self, logger, client_info):
        # Should NOT mark the stream as consumed and safely exit when:
        # - On last retry of transport error
        # - near the head of the stream
        # - heartbeat RAISES AN ERROR
        # - all formats have been initialized
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'transport',
            'rn': list(range(10, 30)),
        })
        heartbeat_callback = MagicMock()
        # raise an error on callback
        heartbeat_callback.side_effect = Exception('heartbeat error')
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = []

        with pytest.raises(TransportError, match='simulated transport error'):
            for part in sabr_stream.iter_parts():
                parts.append(part)

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()
        logger.warning.assert_any_call(
            'Error occurred while calling heartbeat callback, skipping heartbeat check: heartbeat error')
        logger.debug.assert_any_call('Heartbeat does not indicate stream has finished; not marking stream as consumed on last retry')

    @mock_time
    def test_error_at_end_heartbeat_still_live(self, logger, client_info):
        # Should NOT mark the stream as consumed and safely exit when:
        # - On last retry of transport error
        # - near the head of the stream
        # - heartbeat STRICTLY INDICATES STREAM IS STILL LIVE
        # - all formats have been initialized
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        heartbeat_callback = MagicMock()

        def safe_still_live_func(parts, vpabr, url, request_number):
            # Update the callback to is_live=False after many requests,
            # to avoid infinite loop in case of code error
            is_live = True
            if request_number > 100:
                is_live = False
            heartbeat_callback.return_value = Heartbeat(
                is_live=is_live, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')
            return parts

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': safe_still_live_func,
            'mode': 'transport',
            'rn': list(range(10, 30)),
        })

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = []

        with pytest.raises(TransportError, match='simulated transport error'):
            for part in sabr_stream.iter_parts():
                parts.append(part)

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Heartbeat should have been called at least once
        heartbeat_callback.assert_called()
        logger.debug.assert_any_call(
            'Heartbeat does not indicate stream has finished; not marking stream as consumed on last retry')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_error_at_end_not_near_head(self, logger, client_info, post_live):
        # Should NOT mark the stream as consumed and safely exit when:
        # - On last retry of transport error
        # - NOT near the head of the stream
        # - heartbeat indicates stream is not live
        # - all formats have been initialized
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'transport',
            'rn': list(range(2, 30)),  # not near the head of the stream
        })
        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
            post_live=post_live,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = []

        with pytest.raises(TransportError, match='simulated transport error'):
            for part in sabr_stream.iter_parts():
                parts.append(part)

        # It should the first segments
        assert_media_sequence_in_order(parts, audio_selector, 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Callback should not have been called - check for near head should happen before heartbeat check
        heartbeat_callback.assert_not_called()

        logger.debug.assert_any_call('Not near live stream head; not marking stream as consumed on last retry')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_error_at_end_no_live_metadata(self, logger, client_info, post_live):
        # Should NOT mark the stream as consumed and safely exit when:
        # - On last retry of transport error
        # - NO live metadata available (so cannot determine if near head or not)
        # - heartbeat indicates stream is not live
        # - all formats have been initialized
        # logger = SabrFDLogger(ydl=YoutubeDL({'verbose': True}), prefix='live', log_level=SabrFDLogger.LogLevel.TRACE)
        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9

        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        profile = LiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'omit_live_metadata': True,  # no live metadata
            'mode': 'transport',
            'rn': list(range(10, 30)),
        })

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
            post_live=post_live,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, video_selector = selectors

        parts = []

        with pytest.raises(TransportError, match='simulated transport error'):
            for part in sabr_stream.iter_parts():
                parts.append(part)

        # It should get all but the last segment (9)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)
        assert_media_sequence_in_order(parts, video_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Both formats should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 2

        # Callback should not have been called - check for live metadata should happen before heartbeat check
        heartbeat_callback.assert_not_called()

        # No live metadata should available
        assert sabr_stream.processor.live_state is None

        logger.debug.assert_any_call('No live metadata available; not marking stream as consumed on last retry')

    @mock_time
    @pytest.mark.parametrize('post_live', [False, True], ids=['live', 'post_live'])
    def test_error_at_end_missing_izf(self, logger, client_info, post_live):
        # Should NOT mark the stream as consumed and safely exit when:
        # - On last retry for transport errors
        # - near the head of the stream
        # - heartbeat strictly indicates stream is no longer live
        # - NOT all formats have been initialized
        # NOTE: This technically would only happen on a VERY short stream... pretty much unheard of

        total_segments = 2
        segment_target_duration_ms = 2000
        dvr_segments = 1

        heartbeat_callback = MagicMock()
        heartbeat_callback.return_value = Heartbeat(
            is_live=False, broadcast_id=LIVE_BROADCAST_ID, video_id='video_id')

        class MissingAudioFormatLiveRetryAVProfile(LiveRetryAVProfile):
            def determine_formats(self, vpabr: VideoPlaybackAbrRequest):
                audio_format_id, _ = super().determine_formats(vpabr)
                return audio_format_id, None

        profile = MissingAudioFormatLiveRetryAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'mode': 'transport',
            'rn': list(range(2, 30)),
        })

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
            heartbeat_callback=heartbeat_callback,
            post_live=post_live,
        )
        assert sabr_stream.http_retries == 10  # default of 10 retries
        audio_selector, _ = selectors

        parts = []

        with pytest.raises(TransportError, match='simulated transport error'):
            for part in sabr_stream.iter_parts():
                parts.append(part)

        # It should get all but the last segment (1)
        assert_media_sequence_in_order(parts, audio_selector, total_segments - 1, check_segment_total_segments=False)

        # There should be 10 error requests recorded
        error_requests = [d for d in rh.request_history if d.error is not None]
        assert len(error_requests) == 11
        for request in error_requests:
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

        # Should have 10 fallback attempts logged
        for i in range(1, 10):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        # Only one format should have been initialized
        assert len(sabr_stream.processor.initialized_formats) == 1

        # Callback should not have been called - check for missing initialized format should happen before heartbeat check
        heartbeat_callback.assert_not_called()

        logger.debug.assert_any_call(
            'Not all enabled format selectors have an initialized format yet; not marking stream as consumed on last retry')
