from __future__ import annotations
import io
import protobug
import pytest

from test.test_sabr.test_stream.helpers import (
    VIDEO_PLAYBACK_USTREAMER_CONFIG,
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    SabrRequestHandler,
    CustomAVProfile,
    assert_media_sequence_in_order,
    setup_sabr_stream_av,
)
from yt_dlp.extractor.youtube._proto.videostreaming.reload_player_response import ReloadPlaybackParams
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import (
    SabrStreamError,
    StreamStallError,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart
from yt_dlp.networking.exceptions import TransportError

from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector
from yt_dlp.extractor.youtube._streaming.sabr.part import RefreshPlayerResponseSabrPart
from yt_dlp.extractor.youtube._streaming.sabr.stream import SabrStream
from yt_dlp.extractor.youtube._proto.videostreaming import ReloadPlayerResponse


def test_no_new_segments_default(logger, client_info):
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
    with pytest.raises(StreamStallError, match=r'Stream stalled; no activity detected in 3 consecutive requests'):
        list(sabr_stream.iter_parts())

    # Should have made 3 requests before failing
    assert len(rh.request_history) == 3

    stats_str = sabr_stream.create_stats_str()
    assert 'sr:3' in stats_str
    assert 'rn:3' in stats_str
    assert 'act:N' in stats_str


def test_no_new_segments_custom(logger, client_info):
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
    with pytest.raises(StreamStallError, match=r'Stream stalled; no activity detected in 5 consecutive requests'):
        list(sabr_stream.iter_parts())

    # Should have made 5 requests before failing
    assert len(rh.request_history) == 5


def test_no_new_segments_reset_on_new_segment(logger, client_info):
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

    logger.debug.assert_any_call('No activity detected in request 1; registering stall (count: 1)')
    logger.debug.assert_any_call('No activity detected in request 2; registering stall (count: 2)')
    assert rh.request_history[0].parts == rh.request_history[1].parts == []
    assert rh.request_history[2].parts
    logger.debug.assert_any_call('No activity detected in request 4; registering stall (count: 1)')
    logger.debug.assert_any_call('No activity detected in request 5; registering stall (count: 2)')
    assert rh.request_history[3].parts == rh.request_history[4].parts == []
    assert rh.request_history[5].parts


def test_max_empty_requests_negative(logger, client_info):
    # Should raise ValueError if max_empty_requests is negative
    with pytest.raises(ValueError, match='max_empty_requests must be greater than 0'):
        setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            max_empty_requests=-1,
        )


def test_no_new_segments_http_retry_then_segments(logger, client_info):
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


def test_no_new_segments_http_retry_no_segments(logger, client_info):
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
    with pytest.raises(SabrStreamError, match=r'Stream stalled; no activity detected in 3 consecutive requests'):
        list(sabr_stream.iter_parts())

    # Should have made 4 requests before failing (3 empty + 1 retried)
    assert len(rh.request_history) == max_empty_requests + 1

    assert rh.request_history[0].parts == rh.request_history[1].parts == []
    assert isinstance(rh.request_history[2].error, TransportError)
    assert rh.request_history[3].parts == []


def test_no_new_segments_http_retry_with_segments_reset(logger, client_info):
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
    logger.debug.assert_any_call('No activity detected in request 1; registering stall (count: 1)')
    logger.debug.assert_any_call('No activity detected in request 2; registering stall (count: 2)')
    assert isinstance(rh.request_history[2].error, TransportError)
    assert rh.request_history[2].parts  # Has new segments

    assert rh.request_history[3].parts == rh.request_history[4].parts == []
    logger.debug.assert_any_call('No activity detected in request 4; registering stall (count: 1)')
    logger.debug.assert_any_call('No activity detected in request 5; registering stall (count: 2)')
    assert isinstance(rh.request_history[5].error, TransportError)
    assert rh.request_history[5].parts  # Has new segments

    logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')


def test_consumed_segments_counted(logger, client_info):
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
    with pytest.raises(SabrStreamError, match=r'Stream stalled; no activity detected in 3 consecutive requests'):
        list(sabr_stream.iter_parts())

    # Should have made 5 requests before failing (2 normal + 3 empty)
    assert len(rh.request_history) == 2 + max_empty_requests
    logger.debug.assert_any_call('No activity detected in request 3; registering stall (count: 1)')
    logger.debug.assert_any_call('No activity detected in request 4; registering stall (count: 2)')


@pytest.mark.skip(reason='todo')
def test_discarded_segments_not_counted(logger, client_info):
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

    rh = SabrRequestHandler(
        sabr_response_processor=CustomAVProfile({'custom_parts_function': no_new_segments_discarded_func}))
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
