from __future__ import annotations
import io
import pytest

from test.test_sabr.test_stream.helpers import (
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    CustomAVProfile,
    assert_media_sequence_in_order,
    setup_sabr_stream_av,
    collect_parts,
)
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import (
    SabrStreamError,
    StreamStallError,
)
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart
from yt_dlp.networking.exceptions import TransportError


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
        collect_parts(sabr_stream)

    # Should have made 3 requests before failing
    assert len(rh.request_history) == 3

    stats_str = sabr_stream.create_stats_str()
    assert 'sr:3' in stats_str
    assert 'rn:3' in stats_str
    assert 'act:N' in stats_str

    # All responses should be closed
    assert all(request.response.closed for request in rh.request_history)


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
        collect_parts(sabr_stream)

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
    parts = collect_parts(sabr_stream)
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
    parts = collect_parts(sabr_stream)
    assert len(rh.request_history) == 6 + max_empty_requests
    audio_selector, video_selector = selectors
    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    assert rh.request_history[0].parts == rh.request_history[1].parts == []
    assert isinstance(rh.request_history[2].error, TransportError)
    logger.warning.assert_any_call('Got error: simulated transport error. Retrying (1/10)...')


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
        collect_parts(sabr_stream)

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
    parts = collect_parts(sabr_stream)

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

    logger.warning.assert_any_call('Got error: simulated transport error. Retrying (1/10)...')


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
        collect_parts(sabr_stream)

    # Should have made 5 requests before failing (2 normal + 3 empty)
    assert len(rh.request_history) == 2 + max_empty_requests
    logger.debug.assert_any_call('No activity detected in request 3; registering stall (count: 1)')
    logger.debug.assert_any_call('No activity detected in request 4; registering stall (count: 2)')


def test_no_segments_after_initialization(logger, client_info):
    # Should stall if no media segments were provided after format initialization
    max_empty_requests = 3

    def only_format_init_part(parts, vpabr, url, request_number):
        return [part for part in parts if part.part_id == UMPPartId.FORMAT_INITIALIZATION_METADATA]

    sabr_stream, rh, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        sabr_response_processor=CustomAVProfile({'custom_parts_function': only_format_init_part}),
        max_empty_requests=max_empty_requests)

    with pytest.raises(SabrStreamError, match=r'Stream stalled; no activity detected in 3 consecutive requests'):
        collect_parts(sabr_stream)

    assert len(rh.request_history) == max_empty_requests
    logger.debug.assert_any_call('No activity detected in request 3; registering stall (count: 3)')
    logger.debug.assert_any_call(
        'Skipping player time increment; one or more initialized formats is missing a consumed range for current player time')


def test_no_parts(logger, client_info):
    # Should stall if no parts whatsoever were returned
    max_empty_requests = 3

    def no_parts_func(parts, vpabr, url, request_number):
        return []

    sabr_stream, rh, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        sabr_response_processor=CustomAVProfile({'custom_parts_function': no_parts_func}),
        max_empty_requests=max_empty_requests)

    with pytest.raises(SabrStreamError, match=r'Stream stalled; no activity detected in 3 consecutive requests'):
        collect_parts(sabr_stream)

    assert len(rh.request_history) == max_empty_requests
    logger.debug.assert_any_call('No activity detected in request 3; registering stall (count: 3)')
