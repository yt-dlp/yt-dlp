from __future__ import annotations
import base64
import io
import time
from unittest.mock import Mock
import pytest

from test.test_sabr.test_stream.helpers import (
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    CustomAVProfile,
    assert_media_sequence_in_order,
    create_inject_read_error,
    PoTokenAVProfile,
    mock_time,
    setup_sabr_stream_av,
)
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import PoTokenError
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart
from yt_dlp.networking.exceptions import TransportError

from yt_dlp.extractor.youtube._streaming.sabr.part import PoTokenStatusSabrPart
from yt_dlp.extractor.youtube._proto.videostreaming import VideoPlaybackAbrRequest

DEFAULT_RETRIES = 5


def test_sps_ok(logger, client_info):
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

    stats_str = sabr_stream.create_stats_str()
    assert 'pot:Y' in stats_str
    assert 'sps:OK' in stats_str


def test_sps_retry_on_required(logger, client_info):
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
            if count == DEFAULT_RETRIES:
                sabr_stream.processor.po_token = base64.b64encode(b'simulated_po_token_data')
        parts.append(part)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    # Should have 2 PoTokenStatusSabrPart parts indicating Missing, then the following are all OK
    po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
    assert len(po_token_status_parts) >= DEFAULT_RETRIES
    for part in po_token_status_parts[:DEFAULT_RETRIES]:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.MISSING
    for part in po_token_status_parts[DEFAULT_RETRIES:]:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.OK

    # Second request should be a retry of the first, so playback time should be the same
    retry_request_vpabr = rh.request_history[1].vpabr
    assert retry_request_vpabr.client_abr_state.player_time_ms == rh.request_history[
        0].vpabr.client_abr_state.player_time_ms

    for i in range(1, DEFAULT_RETRIES):
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')


def test_no_retry_on_pending(logger, client_info):
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


def test_pending_then_required_retry(logger, client_info):
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
            if count == (pending_requests + DEFAULT_RETRIES):
                sabr_stream.processor.po_token = base64.b64encode(b'simulated_po_token_data')
        parts.append(part)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    # Should have 2 PoTokenStatusSabrPart parts indicating Missing, then the following are all OK
    po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
    for part in po_token_status_parts[:pending_requests]:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.PENDING
    for part in po_token_status_parts[pending_requests:DEFAULT_RETRIES + pending_requests]:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.MISSING
    for part in po_token_status_parts[pending_requests + DEFAULT_RETRIES:]:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.OK

    for i in range(1, DEFAULT_RETRIES + 1):
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')


def test_sps_required_retries_exhausted(logger, client_info):
    # Should raise PoTokenError after exhausting retries when StreamProtectionStatus is REQUIRED
    sabr_stream, rh, _ = setup_sabr_stream_av(
        sabr_response_processor=PoTokenAVProfile(),
        client_info=client_info,
        logger=logger,
    )
    sabr_stream.processor.po_token = None

    parts = []
    with pytest.raises(PoTokenError, match='This stream requires a GVS PO Token to continue'):
        for part in sabr_stream.iter_parts():
            parts.append(part)

    # Should have 6 PoTokenStatusSabrPart parts indicating missing
    po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
    assert len(po_token_status_parts) == DEFAULT_RETRIES + 1
    for part in po_token_status_parts:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.MISSING

    for i in range(1, DEFAULT_RETRIES + 1):
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')

    for request_details in rh.request_history[1:]:
        assert not any(isinstance(part, PoTokenStatusSabrPart) for part in request_details.parts)

    stats_str = sabr_stream.create_stats_str()
    assert 'pot:N' in stats_str
    assert 'sps:ATTESTATION_REQUIRED' in stats_str


def test_sps_invalid_retries_exhausted(logger, client_info):
    # Should raise PoTokenError after exhausting retries when StreamProtectionStatus is INVALID
    sabr_stream, _, _ = setup_sabr_stream_av(
        sabr_response_processor=PoTokenAVProfile(),
        client_info=client_info,
        logger=logger,
    )
    sabr_stream.processor.po_token = base64.b64encode(b'invalid')

    parts = []
    with pytest.raises(PoTokenError,
                       match='This stream requires a GVS PO Token to continue and the one provided is invalid'):
        for part in sabr_stream.iter_parts():
            parts.append(part)

    # Should have 6 PoTokenStatusSabrPart parts indicating invalid
    po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
    assert len(po_token_status_parts) == DEFAULT_RETRIES + 1
    for part in po_token_status_parts:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.INVALID

    for i in range(1, DEFAULT_RETRIES + 1):
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue and the one provided is invalid. Retrying ({i}/5)...')


def test_sps_retry_server_stops_sending_sps(logger, client_info):
    # Should continue to retry if StreamProtectionStatus is REQUIRED
    # and the server stops sending SPS status parts

    class RemoveSPSAfterFirstRequest(PoTokenAVProfile):
        def get_parts(self, vpabr: VideoPlaybackAbrRequest, url: str, request_number: int) -> list[
                UMPPart | Exception]:
            parts = super().get_parts(vpabr, url, request_number)
            if request_number > 1:
                parts = [part for part in parts if not isinstance(part, PoTokenStatusSabrPart)]
            return parts

    sabr_stream, rh, _ = setup_sabr_stream_av(
        sabr_response_processor=RemoveSPSAfterFirstRequest(),
        client_info=client_info,
        logger=logger,
    )
    parts = []
    with pytest.raises(PoTokenError, match='This stream requires a GVS PO Token to continue'):
        for part in sabr_stream.iter_parts():
            parts.append(part)

    # Should have 6 PoTokenStatusSabrPart parts indicating missing
    po_token_status_parts = [part for part in parts if isinstance(part, PoTokenStatusSabrPart)]
    assert len(po_token_status_parts) == DEFAULT_RETRIES + 1
    for part in po_token_status_parts:
        assert part.status == PoTokenStatusSabrPart.PoTokenStatus.MISSING

    for i in range(1, DEFAULT_RETRIES + 1):
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')

    for request_details in rh.request_history[1:]:
        assert not any(isinstance(part, PoTokenStatusSabrPart) for part in request_details.parts)


def test_required_exceed_max_retries(logger, client_info):
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
    for i in range(1, DEFAULT_RETRIES + 1):
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/5)...')


def test_pot_retries_options(logger, client_info):
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
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/3)...')


@mock_time
def test_pot_retry_sleep_func(logger, client_info):
    # Should call the retry_sleep_func between retries to get the sleep duration
    sleep_mock = Mock()
    sleep_mock.side_effect = lambda n: 2.5

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
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/3)...')
    # Should log the sleep
    logger.info.assert_any_call('Sleeping 2.50 seconds ...')
    time.sleep.assert_called_with(2.5)


def test_pot_http_retries(logger, client_info):
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
        return create_inject_read_error([0, 1, 2, 3], part_id=UMPPartId.SNACKBAR_MESSAGE, occurance=1)(parts, vpabr,
                                                                                                       url,
                                                                                                       request_number)

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
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/2)...')
        logger.warning.assert_any_call(f'[sabr] Got error: simulated read error. Retrying ({i}/2)...')


def test_pot_http_retries_diff(logger, client_info):
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
        return create_inject_read_error([0, 1, 2, 3], part_id=UMPPartId.SNACKBAR_MESSAGE, occurance=1)(parts, vpabr,
                                                                                                       url,
                                                                                                       request_number)

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
        logger.warning.assert_any_call(
            f'[sabr] Got error: This stream requires a GVS PO Token to continue. Retrying ({i}/2)...')
        logger.warning.assert_any_call(f'[sabr] Got error: simulated read error. Retrying ({i}/3)...')
