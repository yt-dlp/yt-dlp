from __future__ import annotations
import io
import time
from unittest.mock import Mock
import protobug
import pytest
import urllib.parse

from test.test_sabr.test_stream.helpers import (
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    extract_rn,
    RequestRetryAVProfile,
    CustomAVProfile,
    assert_media_sequence_in_order,
    create_inject_read_error,
    mock_time,
    setup_sabr_stream_av,
)
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import SabrStreamError
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart
from yt_dlp.networking.exceptions import TransportError, HTTPError, RequestError

from yt_dlp.extractor.youtube._streaming.sabr.part import RefreshPlayerResponseSabrPart
from yt_dlp.extractor.youtube._proto.videostreaming import SabrError


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

    @mock_time
    def test_http_retry_sleep_func(self, logger, client_info):
        # Should call the retry_sleep_func between retries to get the sleep duration
        sleep_mock = Mock()
        sleep_mock.side_effect = lambda n: 2.5

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
        logger.info.assert_any_call('Sleeping 2.50 seconds ...')
        time.sleep.assert_called_with(2.5)

    def test_expiry_on_retry(self, logger, client_info):
        # Should check for expiry before retrying and yield RefreshPlayerResponseSabrPart if within threshold
        expires_at = int(time.time() + 30)  # 30 seconds from now
        sabr_stream, _, __ = setup_sabr_stream_av(
            sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(7))}),
            client_info=client_info,
            logger=logger,
            url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
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
            sabr_response_processor=CustomAVProfile({'custom_parts_function': lambda parts, vpabr, url,
                                                     request_number: [
                                                         TransportError('simulated SABR response error')] if request_number == 2 else parts}),
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
            return create_inject_read_error([6], part_id=UMPPartId.SNACKBAR_MESSAGE, occurance=1)(parts, vpabr, url,
                                                                                                  request_number)

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
        logger.warning.assert_any_call(
            "[sabr] Got error: SABR Protocol Error: SabrError(type='simulated SABR error', action=1, error=None). Retrying (1/10)...")


class TestGVSFallbackRetries:
    def test_gvs_fallback_after_8_retries_transport_error(self, logger, client_info):
        # Should fallback to next gvs server after max retries exceeded on transport error
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 10))}),
            client_info=client_info,
            logger=logger,
            url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6&sabr=1',
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
            following_request_url = urllib.parse.urlparse(following_request.request.url)
            assert following_request_url.netloc == 'rr3---sn-7654321.googlevideo.com'
            assert 'fallback_count=1' in following_request_url.query

        # Check request before fallback
        last_error_request_url = urllib.parse.urlparse(last_error_request.request.url)
        assert last_error_request_url.netloc == 'rr6---sn-6942067.googlevideo.com'

        # Should have 8 fallback attempts logged
        for i in range(1, 9):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        logger.warning.assert_any_call('Falling back to host rr3---sn-7654321.googlevideo.com')

    def test_gvs_fallback_after_8_retries_http_error(self, logger, client_info):
        # Should fallback to next gvs server after max retries exceeded on http error
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=RequestRetryAVProfile({'mode': 'http', 'rn': list(range(2, 10))}),
            client_info=client_info,
            logger=logger,
            url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6&sabr=1',
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
            assert isinstance(request.error, HTTPError)
            assert request.error.status == 500

        # Check that the host was switched after 8 retries
        last_error_request = error_requests[-1]
        for following_request in rh.request_history[rh.request_history.index(last_error_request) + 1:]:
            following_request_url = urllib.parse.urlparse(following_request.request.url)
            assert following_request_url.netloc == 'rr3---sn-7654321.googlevideo.com'
            assert 'fallback_count=1' in following_request_url.query

        # Check request before fallback
        last_error_request_url = urllib.parse.urlparse(last_error_request.request.url)
        assert last_error_request_url.netloc == 'rr6---sn-6942067.googlevideo.com'

        # Should have 8 fallback attempts logged
        for i in range(1, 9):
            logger.warning.assert_any_call(
                f'[sabr] Got error: HTTP Error 500: Internal Server Error. Retrying ({i}/10)...')

        logger.warning.assert_any_call('Falling back to host rr3---sn-7654321.googlevideo.com')

    def test_gvs_fallback_multiple_hosts(self, logger, client_info):
        # Should keep falling back to next gvs server until default max total attempts exceeded
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
            client_info=client_info,
            logger=logger,
            url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321,sn-0000000-0000&fvip=3&mvi=6&sabr=1',
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
        retry_request_one_url = urllib.parse.urlparse(retry_request_one.request.url)
        assert retry_request_one_url.netloc == 'rr3---sn-7654321.googlevideo.com'
        assert 'fallback_count=1' in retry_request_one_url.query
        logger.warning.assert_any_call('Falling back to host rr3---sn-7654321.googlevideo.com')

        retry_request_two = error_requests[9]  # second fallback
        retry_request_two_url = urllib.parse.urlparse(retry_request_two.request.url)
        assert retry_request_two_url.netloc == 'rr3---sn-0000000-0000.googlevideo.com'
        assert 'fallback_count=2' in retry_request_two.request.url
        logger.warning.assert_any_call('Falling back to host rr3---sn-0000000-0000.googlevideo.com')

        # No more fallbacks, should stay on the same host for the remaining retries until giving up
        retry_request_three = error_requests[10]  # third fallback attempt before giving up
        retry_request_three_url = urllib.parse.urlparse(retry_request_three.request.url)
        assert retry_request_three_url.netloc == 'rr3---sn-0000000-0000.googlevideo.com'
        assert 'fallback_count=2' in retry_request_three.request.url
        logger.debug.assert_any_call('No more fallback hosts available')

    def test_gvs_fallback_threshold_option(self, logger, client_info):
        # Should respect the host_fallback_threshold option for retries before fallback
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 5))}),
            client_info=client_info,
            logger=logger,
            url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6&sabr=1',
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
            following_request_url = urllib.parse.urlparse(following_request.request.url)
            assert following_request_url.netloc == 'rr3---sn-7654321.googlevideo.com'
            assert 'fallback_count=1' in following_request_url.query

        # Request before fallback
        last_error_request_url = urllib.parse.urlparse(last_error_request.request.url)
        assert last_error_request_url.netloc == 'rr6---sn-6942067.googlevideo.com'

        # Should have 4 fallback attempts logged
        for i in range(1, 4):
            logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        logger.warning.assert_any_call('Falling back to host rr3---sn-7654321.googlevideo.com')

    def test_gvs_fallback_no_fallback_available(self, logger, client_info):
        # Should not fallback if there are no fallback options available
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
            client_info=client_info,
            logger=logger,
            url='https://rr6---sn-6942067.googlevideo.com?sabr=1',
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
            request_url = urllib.parse.urlparse(request.request.url)
            assert request_url.netloc == 'rr6---sn-6942067.googlevideo.com'

        assert not any('Falling back to host' in call.args[0] for call in logger.warning.call_args_list)
        logger.debug.assert_any_call('No more fallback hosts available')

    def test_gvs_no_fallback_not_sabr_error(self, logger, client_info):
        # Should not fallback if the error is not a TransportError/HTTPError.
        # For example, on a SabrStreamError from a SABR_ERROR part.

        def sabr_error_injector(parts, vpabr, url, request_number):
            if request_number in list(range(2, 15)):
                message = protobug.dumps(SabrError(action=1, type='simulated SABR error'))
                return [UMPPart(
                    part_id=UMPPartId.SABR_ERROR,
                    size=len(message),
                    data=io.BytesIO(message))]

            return parts

        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=CustomAVProfile({'custom_parts_function': sabr_error_injector}),
            client_info=client_info,
            logger=logger,
            url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6&sabr=1',
        )

        expected_cause = r"SABR Protocol Error: SabrError\(type='simulated SABR error', action=1, error=None\)"
        with pytest.raises(SabrStreamError, match=expected_cause):
            list(sabr_stream.iter_parts())

        # xxx: not recorded as an error in the request history as SabrError is part of normal processing.
        logger.warning.assert_any_call(
            "[sabr] Got error: SABR Protocol Error: SabrError(type='simulated SABR error', action=1, error=None). Retrying (1/10)...")

        # All requests should have the same host
        for request in rh.request_history:
            request_url = urllib.parse.urlparse(request.request.url)
            assert request_url.netloc == 'rr6---sn-6942067.googlevideo.com'
